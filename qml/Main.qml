import QtQuick
import QtQuick.Window

Window {
    id: window
    objectName: "mainWindow"
    width: 1600; height: 720; minimumWidth: 800; minimumHeight: 360
    visible: true; color: "#0E140F"; title: "NEXATOM · v1.4"
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
    function beginMove(side,x,y) {let p=screen.mapFromItem(null,x,y);graphDrag.begin(side,side===0?ctl.leftChannel:ctl.rightChannel,p.x,p.y)}
    function updateMove(x,y) {let p=screen.mapFromItem(null,x,y);graphDrag.move(p.x,p.y)}
    function finishMove(x,y) {let p=screen.mapFromItem(null,x,y);graphDrag.finish(p.x,p.y)}
    Connections { target: ctl; function onChanged() { window.revision++ } }
    Item {
        id: screen; objectName: "screen"
        width: 1600; height: 720
        x: (window.width-width*scale)/2; y: (window.height-height*scale)/2
        scale: Math.min(window.width/1600,window.height/720); transformOrigin: Item.TopLeft
        clip: true
        Rectangle { anchors.fill: parent; color: "#0E140F" }
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
                onGraphMoveStarted: function(s,x,y) {window.beginMove(s,x,y)}
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
                onGraphMoveStarted: function(s,x,y) {window.beginMove(s,x,y)}
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
        }
        GraphDrag {id:graphDrag;objectName:"graphDrag";anchors.fill:parent;visible:false;revision:window.revision}
        ModuleSelector {id:selector;objectName:"selector";anchors.fill:parent;visible:false;onClosed:visible=false}
        NumberPad { id: keypad; objectName: "keypad"; anchors.fill: parent; visible: false; onClosed: visible=false }
        RadialMenu {
            id: radial; objectName: "radialMenu"; anchors.fill: parent; visible: false
            onClosed: visible=false
            onChosen: function(option,index,side) {
                visible=false
                if(option==="Signals") ctl.toggleError(index)
                else if(option==="Settings") ctl.openSettings()
                else if(option==="Display") window.openFullscreen(side)
                else {let c=ctl.channel(index);window.showNotice("Laser "+c.number+" · "+c.status+" · "+(c.stabilised?"Stabilised":"Live"))}
            }
        }
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter; y: 638; width: 850; height: 62
            color: "#000000"; border.width: 1; border.color: "#D9D9D9"; radius: 6
            visible: window.notice!==""
            Text { anchors.centerIn: parent; text: window.notice; color: "white"; font.pixelSize: 23 }
        }
        Rectangle {
            objectName: "bootScreen"; anchors.fill: parent; color: "#0E140F"; visible: window.booting
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
