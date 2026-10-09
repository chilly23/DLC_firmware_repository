import QtQuick
import QtQuick.Window

Window {
    id: window
    objectName: "mainWindow"
    width: 1600; height: 720; minimumWidth: 800; minimumHeight: 360
    visible: true; color: theme.background; title: "NEXATOM · v1.7"
    property bool booting: !skipBoot
    property real bootProgress: 0
    property bool bootStarted: false
    property int revision: 0
    property int fullscreenSide: -1
    property string notice: ""
    property alias keypad: keypad
    property alias radial: radial
    function openEditor(index,key,side,bottom) {keypad.open(index,key,side,bottom)}
    function openFullscreen(side) {
        let bounds=(side===0 ? leftPane : rightPane).viewRange()
        fullscreenView.setViewRange(bounds[0],bounds[1])
        window.fullscreenSide=side
    }
    function closeFullscreen() {
        let bounds=fullscreenView.viewRange()
        ;(window.fullscreenSide===0 ? leftPane : rightPane).setViewRange(bounds[0],bounds[1])
        window.fullscreenSide=-1
    }
    function showNotice(message) { notice=message; noticeTimer.restart() }
    function beginMove(side,errorSignal,x,y) {let p=screen.mapFromItem(null,x,y);graphDrag.begin(side,side===0?ctl.leftChannel:ctl.rightChannel,errorSignal,p.x,p.y)}
    function updateMove(x,y) {let p=screen.mapFromItem(null,x,y);graphDrag.move(p.x,p.y)}
    function finishMove(x,y) {let p=screen.mapFromItem(null,x,y);graphDrag.finish(p.x,p.y)}
    Connections { target: ctl; function onChanged() { window.revision++ } }
    Connections {target:systemSettings;function onNavigateTour(step){
        radial.visible=false;selector.visible=false;keypad.visible=false;signalsPanel.visible=false;alarmPanel.visible=false;window.fullscreenSide=-1
        if(step<0)return
        let info=systemSettings.tour, action=info.action, side=info.side||0
        let index=side===0?ctl.leftChannel:ctl.rightChannel
        if(["signals","combined","axes","error_axes"].indexOf(action)>=0){
            signalsPanel.open(side,index)
            if(action==="combined")ctl.setChartMode(index,"combined")
            else if(action!=="signals"){signalsPanel.axisPage=true;signalsPanel.errorAxis=action==="error_axes"}
        }
        if(action==="fullscreen")window.openFullscreen(side)
        if(action==="more")radial.open(side,index)
        if(action==="alarms")alarmPanel.open(side,index)
        if(action==="numpad")keypad.open(index,ctl.channel(index).top,side,false)
        if(action==="modules"||action==="fields")selector.open(index,ctl.channel(index).top,side,false,action==="modules")
    }}
    Item {
        id: screen; objectName: "screen"
        width: 1600; height: 720
        x: (window.width-width*scale)/2; y: (window.height-height*scale)/2
        scale: Math.min(window.width/1600,window.height/720); transformOrigin: Item.TopLeft
        clip: true
        Rectangle { anchors.fill: parent; color: theme.background }
        Item {
            anchors.fill: parent; visible: !window.booting && window.fullscreenSide < 0
            ChannelPane {
                id: leftPane
                side: 0; channelIndex: ctl.leftChannel; revision: window.revision
                onNotice: function(message) {window.showNotice(message)}
                onEditRequested: function(index,key,side,bottom) {window.openEditor(index,key,side,bottom)}
                onFullscreenRequested: function(side) {window.openFullscreen(side)}
                onMoreRequested: function(side) {radial.open(side,ctl.leftChannel)}
                onSelectorRequested: function(i,k,s,b,m) {selector.open(i,k,s,b,m)}
                onSignalsRequested: function(s,i) {signalsPanel.open(s,i)}
                onGraphMoveStarted: function(s,e,x,y) {window.beginMove(s,e,x,y)}
                onGraphMoveUpdated: function(x,y) {window.updateMove(x,y)}
                onGraphMoveFinished: function(x,y) {window.finishMove(x,y)}
                onGraphMoveCancelled: graphDrag.visible=false
            }
            ChannelPane {
                id: rightPane
                x: 800; side: 1; channelIndex: ctl.rightChannel; revision: window.revision
                onNotice: function(message) {window.showNotice(message)}
                onEditRequested: function(index,key,side,bottom) {window.openEditor(index,key,side,bottom)}
                onFullscreenRequested: function(side) {window.openFullscreen(side)}
                onMoreRequested: function(side) {radial.open(side,ctl.rightChannel)}
                onSelectorRequested: function(i,k,s,b,m) {selector.open(i,k,s,b,m)}
                onSignalsRequested: function(s,i) {signalsPanel.open(s,i)}
                onGraphMoveStarted: function(s,e,x,y) {window.beginMove(s,e,x,y)}
                onGraphMoveUpdated: function(x,y) {window.updateMove(x,y)}
                onGraphMoveFinished: function(x,y) {window.finishMove(x,y)}
                onGraphMoveCancelled: graphDrag.visible=false
            }
            Rectangle { objectName: "divider"; x: 800; width: 4; height: 605; color: "#4A4D47" }
        }
        FullscreenView {
            id: fullscreenView
            anchors.fill: parent; visible: !window.booting && window.fullscreenSide>=0
            channelIndex: window.fullscreenSide===1 ? ctl.rightChannel : ctl.leftChannel
            revision: window.revision
            onClosed: window.closeFullscreen()
            onSignalsRequested: signalsPanel.open(window.fullscreenSide,channelIndex)
        }
        GraphDrag {id:graphDrag;objectName:"graphDrag";anchors.fill:parent;visible:false;revision:window.revision}
        ModuleSelector {id:selector;objectName:"selector";anchors.fill:parent;visible:false;onClosed:visible=false}
        SignalsPanel {id:signalsPanel;objectName:"signalsPanel";anchors.fill:parent;visible:false;revision:window.revision;onEditAxis:function(i,k,s){keypad.open(i,k,s===0?1:0,false)}}
        NumberPad { z: 30; id: keypad; objectName: "keypad"; anchors.fill: parent; visible: false; onClosed: visible=false }
        RadialMenu {
            id: radial; objectName: "radialMenu"; anchors.fill: parent; visible: false
            onClosed: visible=false
            onChosen: function(option,index,side) {
                visible=false
                if(option==="Alarms") alarmPanel.open(side,index)
                else if(option==="Settings") ctl.openSettings()
                else if(option==="Display") window.openFullscreen(side)
                else {let c=ctl.channel(index);window.showNotice("Laser "+c.number+" · "+c.status+" · "+(c.stabilised?"Stabilised":"Live"))}
            }
        }
        AlarmPanel {
            id: alarmPanel; objectName: "alarmPanel"; anchors.fill: parent; visible: false
            revision: window.revision
            onEditRequested: function(index, key, side, lower) { keypad.open(index, key, side, lower) }
        }
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter; y: 638; width: 730; height: 62
            color: theme.surface; border.width: 1; border.color: theme.foreground; radius: 6
            visible: window.notice!==""
            Text { font.family:theme.fontFamily; anchors.centerIn: parent; width:parent.width-24;elide:Text.ElideRight;horizontalAlignment:Text.AlignHCenter;text: window.notice; color: theme.foreground; font.pixelSize: theme.fontSize(23) }
        }
        Rectangle {
            objectName:"alarmBanner"
            property var alerts:{window.revision;return [ctl.alarm(0),ctl.alarm(1)]}
            property int alarmIndex:alerts[0].active?0:1
            visible:!window.booting && window.fullscreenSide<0 && window.notice==="" && (alerts[0].active||alerts[1].active)
            x:441;y:644;width:718;height:54;radius:8;color:theme.surface
            Text {anchors.centerIn:parent;width:690;text:"Laser "+(parent.alarmIndex+1)+" · "+theme.translate(theme.language,"Alarms")+" · "+parent.alerts[parent.alarmIndex].status;elide:Text.ElideRight;color:"#FF453A";font.family:theme.fontFamily;font.pixelSize:18}
            MouseArea {anchors.fill:parent;onClicked:alarmPanel.open(0,parent.alarmIndex)}
        }
        TooltipOverlay {anchors.fill:parent;z:45}
        TourOverlay {anchors.fill:parent;z:50}
        Rectangle {
            z:60;visible:systemSettings.powerSeconds>0;x:430;y:270;width:740;height:200;radius:20;color:theme.surface
            Text {anchors.horizontalCenter:parent.horizontalCenter;y:28;text:"Automatic power action in "+systemSettings.powerSeconds+"s";font.family:theme.fontFamily;font.pixelSize:28;color:theme.foreground}
            TouchButton {x:205;y:109;width:330;height:62;radius:10;normalColor:theme.raised;text:theme.translate(theme.language,"Cancel");onClicked:systemSettings.cancel_power()}
        }
        Rectangle {
            objectName: "bootScreen"; anchors.fill: parent; color: theme.background; visible: window.booting
            Image { x: 482; y: 235; width: 638; height: 202; source: "../assets/logo.png"; fillMode: Image.PreserveAspectFit; smooth: true }
            Rectangle { x: 427; y: 493; width: 798; height: 5; radius: 2.5; color: "#202820"
                Rectangle { height: 5; width: parent.width*window.bootProgress; radius: 2.5; color: "#E8E9E5" }
            }
            MouseArea { anchors.fill: parent }
        }
    }
    Timer { id: noticeTimer; interval: 2800; onTriggered: window.notice="" }
    NumberAnimation { id: bootAnimation; target: window; property: "bootProgress"; from: 0; to: 1; duration: 3000; onFinished: {window.booting=false;ctl.startAcquisition()} }
    Component.onCompleted: {if(skipBoot)ctl.startAcquisition()}
    onFrameSwapped: {
        if(window.booting && !window.bootStarted) {
            window.bootStarted=true
            bootAnimation.start()
        }
    }
}
