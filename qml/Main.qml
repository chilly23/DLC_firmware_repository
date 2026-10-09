import QtQuick
import QtQuick.Window

Window {
    id: window
    objectName: "mainWindow"
    width: 1600; height: 720; minimumWidth: 800; minimumHeight: 360
    visible: true; color: theme.background; title: "NEXATOM · v1.15"
    property bool booting: !skipBoot
    property real bootProgress: 0
    property bool bootStarted: false
    property int revision: 0
    property int fullscreenSide: -1
    property string notice: ""
    property alias keypad: keypad
    property alias radial: radial
    property alias logsWindow: logsWindow
    property alias lobby: lobby
    property var guideState:null
    function saveGuide(){
        if(guideState)return
        guideState={lobbyVisible:lobby.visible,lobbyPage:lobby.page,fullscreen:fullscreenSide,left:leftPane.viewRange(),right:rightPane.viewRange(),full:fullscreenView.viewRange(),
            signals:signalsPanel.visible,side:signalsPanel.side,index:signalsPanel.channelIndex,axes:signalsPanel.axisPage,error:signalsPanel.errorAxis}
    }
    function restoreGuide(){
        if(!guideState)return
        let s=guideState;guideState=null;leftPane.setViewRange(s.left[0],s.left[1]);rightPane.setViewRange(s.right[0],s.right[1]);fullscreenView.setViewRange(s.full[0],s.full[1]);fullscreenSide=s.fullscreen
        lobby.page=s.lobbyPage;lobby.visible=s.lobbyVisible
        if(s.signals){signalsPanel.open(s.side,s.index);signalsPanel.axisPage=s.axes;signalsPanel.errorAxis=s.error}
    }
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
    function showNotice(message) { ctl.notify(message) }
    function panelInput(key){let side=key.indexOf("right_")===0?1:0,index=side===0?ctl.leftChannel:ctl.rightChannel;if(key.indexOf("emission")>=0){if(ctl.settingsVisible())ctl.closeSettings();emissionConfirm.physicalPress(side,index)}else ctl.runShortcut(side)}
    function performKnob(action,corner,amount){
        let side=corner<2?0:1,index=side===0?ctl.leftChannel:ctl.rightChannel,lower=corner%2===1
        let channel=ctl.channel(index),key=lower?channel.bottom:channel.top
        if(action==="value.increase"||action==="value.decrease"){
            if(fullscreenSide>=0 && !keypad.visible)closeFullscreen()
            let delta=(action==="value.increase"?1:-1)*amount
            if(keypad.visible){let result=navigation.stepDraft(keypad.fieldKey,keypad.draft,keypad.cursor,delta);keypad.draft=result.text;keypad.cursor=result.cursor;keypad.errorMessage=result.error;keypad.replaceDraft=false}
            else navigation.adjustCorner(corner,delta)
            return
        }
        if(action==="cursor.left"||action==="cursor.right"){
            if(fullscreenSide>=0 && !keypad.visible)closeFullscreen()
            if(keypad.visible){keypad.replaceDraft=false;keypad.cursor=Math.max(0,Math.min(keypad.draft.length,keypad.cursor+(action==="cursor.left"?-amount:amount)))}
            else navigation.moveDigit(corner,(action==="cursor.left"?1:-1)*amount)
            return
        }
        if(action==="editor.open"){keypad.open(index,key,side,lower);return}
        if(action.indexOf("graph.")===0 && fullscreenSide>=0 && fullscreenSide!==side){closeFullscreen();openFullscreen(side)}
        if(action==="graph.lock")ctl.toggleLock(index)
        else if(action.indexOf("graph.")===0){
            if(channel.locked){showNotice("View locked. Unlock it to pan or zoom.");return}
            if(window.fullscreenSide>=0)fullscreenView.nudge(action,amount)
            else (side===0?leftPane:rightPane).nudge(action,amount)
        }
        else if(action==="emission.toggle")emissionConfirm.open(side,index)
        else if(action==="stabilise.toggle")ctl.toggleStabilisation(index)
        else if(action==="view.swap")ctl.switchView(side)
        else if(action==="view.fullscreen"){if(fullscreenSide>=0)closeFullscreen();else openFullscreen(side)}
        else if(action==="signals.open")signalsPanel.open(side,index)
        else if(action==="more.open"){if(radial.visible&&radial.side===side)radial.dismiss("");else radial.open(side,index)}
    }
    function dismissKnobPanel(){
        if(systemSettings.tourIndex>=0){systemSettings.stopTour();return}
        if(tooltip.visible){tooltip.visible=false;return}
        if(emissionConfirm.visible){emissionConfirm.cancel();return}
        if(keypad.visible){keypad.visible=false;return}
        if(signalsPanel.visible){if(signalsPanel.axisPage)signalsPanel.axisPage=false;else signalsPanel.visible=false;return}
        if(alarmPanel.visible){alarmPanel.visible=false;return}
        if(radial.visible){radial.dismiss("");return}
        if(selector.visible){if(!selector.modules)selector.modules=true;else selector.visible=false;return}
        if(lobby.visible){lobby.back();return}
        if(fullscreenSide>=0){closeFullscreen();return}
        showNotice("Home · hold a knob push to exit navigation")
    }
    function beginMove(side,errorSignal,x,y) {let p=screen.mapFromItem(null,x,y);graphDrag.begin(side,side===0?ctl.leftChannel:ctl.rightChannel,errorSignal,p.x,p.y)}
    function updateMove(x,y) {let p=screen.mapFromItem(null,x,y);graphDrag.move(p.x,p.y)}
    function finishMove(x,y) {let p=screen.mapFromItem(null,x,y);graphDrag.finish(p.x,p.y)}
    function cancelInputForLock(){graphDrag.visible=false;lobby.visible=false;logsWindow.dismiss();if(emissionConfirm.visible)emissionConfirm.cancel();if(radial.visible)radial.dismiss("")}
    Connections {target:workspace
        function onPageRequested(page){ctl.closeSettings();lobby.open(page)}
        function onLogsRequested(){ctl.closeSettings();logsWindow.open()}
        function onCloseLogsRequested(){logsWindow.dismiss()}
    }
    LogsWindow {id:logsWindow;homeWindow:window}
    Connections { target: ctl; function onChanged() { window.revision++ }  }
    Connections {target:systemSettings;function onNavigateTour(step){
        radial.visible=false;selector.visible=false;keypad.visible=false;signalsPanel.visible=false;alarmPanel.visible=false;window.fullscreenSide=-1
        signalsPanel.tourMode=""
        if(step<0){restoreGuide();return}
        lobby.visible=false
        let info=systemSettings.tour, action=info.action, side=info.side||0
        let index=side===0?ctl.leftChannel:ctl.rightChannel
        if(["signals","combined","axes","error_axes"].indexOf(action)>=0){
            signalsPanel.open(side,index)
            if(action==="combined")signalsPanel.tourMode="combined"
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
            anchors.fill: parent; visible: !window.booting && window.fullscreenSide < 0 && !lobby.visible
            ChannelPane {
                id: leftPane
                side: 0; channelIndex: ctl.leftChannel; revision: window.revision
                onNotice: function(message) {window.showNotice(message)}
                onEditRequested: function(index,key,side,bottom) {window.openEditor(index,key,side,bottom)}
                onFullscreenRequested: function(side) {window.openFullscreen(side)}
                onMoreRequested: function(side) {radial.open(side,ctl.leftChannel)}
                onEmissionRequested:function(side,index){emissionConfirm.open(side,index)}
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
                onEmissionRequested:function(side,index){emissionConfirm.open(side,index)}
                onSelectorRequested: function(i,k,s,b,m) {selector.open(i,k,s,b,m)}
                onSignalsRequested: function(s,i) {signalsPanel.open(s,i)}
                onGraphMoveStarted: function(s,e,x,y) {window.beginMove(s,e,x,y)}
                onGraphMoveUpdated: function(x,y) {window.updateMove(x,y)}
                onGraphMoveFinished: function(x,y) {window.finishMove(x,y)}
                onGraphMoveCancelled: graphDrag.visible=false
            }
            Rectangle { objectName: "divider"; x: 798; width: 4; height: 605; color: "#4A4D47" }
        }
        FullscreenView {
            id: fullscreenView
            anchors.fill: parent; visible: !window.booting && window.fullscreenSide>=0 && !lobby.visible
            channelIndex: window.fullscreenSide===1 ? ctl.rightChannel : ctl.leftChannel
            revision: window.revision
            onClosed: window.closeFullscreen()
            onSignalsRequested: signalsPanel.open(window.fullscreenSide,channelIndex)
        }
        GraphDrag {id:graphDrag;objectName:"graphDrag";anchors.fill:parent;visible:false;revision:window.revision}
        ModuleSelector {z:25;id:selector;objectName:"selector";anchors.fill:parent;visible:false;onClosed:visible=false}
        SignalsPanel {id:signalsPanel;objectName:"signalsPanel";anchors.fill:parent;visible:false;revision:window.revision;onEditAxis:function(i,k,s){keypad.open(i,k,s===0?1:0,false);keypad.ownerSide=s}}
        NumberPad { z: 30; id: keypad; objectName: "keypad"; anchors.fill: parent; visible: false; onClosed: visible=false }
        RadialMenu {
            id: radial; objectName: "radialMenu"; anchors.fill: parent; visible: false
            onClosed: visible=false
            onChosen: function(option,index,side) {
                visible=false
                if(option==="Alarms") alarmPanel.open(side,index)
                else if(option==="Settings") ctl.openSettings()
                else if(option==="Logs") logsWindow.open()
                else if(option==="Lobby") lobby.open("lobby")
                else if(option==="Notifications")ctl.openSection("notifications")
                else ctl.openSection("control")
            }
        }
        Lobby {
            id:lobby;z:18;anchors.fill:parent;visible:false
            onClosed:visible=false
            onLogsRequested:logsWindow.open()
            onEditParameter:function(index,key){keypad.open(index,key,index,false)}
            onChooseHomeField:function(side,bottom){let index=side===0?ctl.leftChannel:ctl.rightChannel;let ch=ctl.channel(index);selector.open(index,bottom?ch.bottom:ch.top,side,bottom,true)}
        }
        AlarmPanel {
            id: alarmPanel; objectName: "alarmPanel"; anchors.fill: parent; visible: false
            revision: window.revision
            onEditRequested: function(index, key, side, lower) { keypad.open(index, key, side, lower) }
        }
        Rectangle {
            x:590;y:611;width:420;height:28;radius:6;color:theme.surface
            visible:knobs.navigationMode && !window.booting
            Text {anchors.centerIn:parent;text:"Knob navigation · hold push to exit";color:theme.foreground;font.family:theme.fontFamily;font.pixelSize:16}
        }
        NotificationToast {objectName:"notificationToast"}
        EmissionConfirm {id:emissionConfirm;objectName:"emissionConfirm";anchors.fill:parent;visible:false}
        Rectangle {
            objectName:"alarmBanner"
            property var alerts:{window.revision;return [ctl.alarm(0),ctl.alarm(1)]}
            property int alarmIndex:alerts[0].active?0:1
            visible:!window.booting && window.fullscreenSide<0 && notifications.toast.text==="" && (alerts[0].active||alerts[1].active)
            x:441;y:644;width:718;height:54;radius:8;color:theme.surface
            Text {anchors.centerIn:parent;width:690;text:"Laser "+(parent.alarmIndex+1)+" · "+theme.translate(theme.language,"Alarms")+" · "+parent.alerts[parent.alarmIndex].status;elide:Text.ElideRight;color:"#FF453A";font.family:theme.fontFamily;font.pixelSize:18}
            MouseArea {anchors.fill:parent;onClicked:alarmPanel.open(0,parent.alarmIndex)}
        }
        TooltipOverlay {id:tooltip;anchors.fill:parent;z:45}
        TourOverlay {anchors.fill:parent;z:50}
        Rectangle {
            objectName:"powerCountdown";z:60;visible:systemSettings.powerSeconds>0;x:430;y:270;width:740;height:200;radius:20;color:theme.surface
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
    Rectangle {
        z:90;visible:navigation.focus.active
        x:navigation.focus.x-3;y:navigation.focus.y-3;width:navigation.focus.width+6;height:navigation.focus.height+6
        radius:8;color:theme.active;border.width:0;border.color:theme.light?"#111111":"#FFFFFF"
        Text {anchors.fill:parent;anchors.margins:6;verticalAlignment:Text.AlignVCenter;horizontalAlignment:Text.AlignHCenter;text:navigation.focus.label;wrapMode:Text.WordWrap;color:theme.activeInk;font.family:theme.fontFamily;font.pixelSize:Math.min(20,parent.height/3);fontSizeMode:Text.Fit;minimumPixelSize:14}
        Rectangle {x:Math.min(0,window.width-parent.x-width-6);y:parent.y>window.height-110?-36:parent.height+4;width:Math.min(440,label.implicitWidth+24);height:32;radius:6;color:theme.active
            Text {id:label;anchors.centerIn:parent;width:parent.width-20;elide:Text.ElideRight;text:navigation.focus.label;font.family:theme.fontFamily;font.pixelSize:16;color:theme.activeInk}
        }
    }
    NumberAnimation { id: bootAnimation; target: window; property: "bootProgress"; from: 0; to: 1; duration: 3000; onFinished: {window.booting=false;ctl.startAcquisition()} }
    Component.onCompleted: {if(skipBoot)ctl.startAcquisition()}
    onFrameSwapped: {
        if(window.booting && !window.bootStarted) {
            window.bootStarted=true
            bootAnimation.start()
        }
    }
}
