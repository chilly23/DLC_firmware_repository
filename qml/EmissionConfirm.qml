import QtQuick
Item {
    id:panel;z:35
    property int side:0
    property int channelIndex:0
    property bool desired:false
    property real progress:0
    property bool confirmed:false
    property double openedAt:0
    function open(paneSide,index){exitAnimation.stop();side=paneSide;channelIndex=index;desired=!ctl.channel(index).emission;progress=0;confirmed=false;visible=true;opacity=1;openedAt=Date.now()}
    function confirm(){if(confirmed||!visible)return;confirmed=true;ctl.setEmission(channelIndex,desired);exitAnimation.restart()}
    function cancel(){confirmed=true;exitAnimation.restart()}
    function physicalPress(paneSide,index){if(visible&&side===paneSide){if(Date.now()-openedAt>500)confirm()}else open(paneSide,index)}
    function rotateSteps(amount){progress=Math.max(0,Math.min(1,progress+amount*.1))}
    function knobConfirm(){if(progress>=.95)confirm();else ctl.notify("Turn the knob to complete the emission slider, then press.")}
    NumberAnimation {id:exitAnimation;target:panel;property:"opacity";to:0;duration:240;onFinished:panel.visible=false}
    Rectangle {anchors.fill:parent;color:"#000000";opacity:.6}
    MouseArea {anchors.fill:parent;onClicked:panel.cancel()}
    Rectangle {
        x:panel.side===0?115:825;y:259;width:660;height:202;radius:24;color:theme.surface
        Text {x:25;y:22;width:535;text:"Laser "+(panel.channelIndex+1)+" · "+(panel.desired?"Enable":"Disable")+" emission";font.family:theme.fontFamily;font.pixelSize:28;color:theme.foreground}
        TouchButton {x:578;y:13;width:60;height:60;iconName:"close";onClicked:panel.cancel()}
        Rectangle {
            id:track;objectName:"emissionTrack";x:25;y:97;width:610;height:78;radius:39;color:theme.raised
            Text {anchors.centerIn:parent;text:"Slide to "+(panel.desired?"enable":"disable");font.family:theme.fontFamily;font.pixelSize:24;color:theme.muted;opacity:1-panel.progress}
            Rectangle {x:4+panel.progress*(parent.width-82);y:4;width:74;height:70;radius:35;color:theme.active
                Icon {anchors.centerIn:parent;width:34;height:34;kind:"chevronRight";ink:theme.activeInk}
            }
            MouseArea {anchors.fill:parent;property bool grabbed:false
                onPressed:function(mouse){grabbed=mouse.x<=90+panel.progress*(width-82)}
                onPositionChanged:function(mouse){if(pressed&&grabbed)panel.progress=Math.max(0,Math.min(1,(mouse.x-41)/(width-82)))}
                onReleased:{if(grabbed&&panel.progress>=.95)panel.confirm();else panel.progress=0;grabbed=false}
                onCanceled:{panel.progress=0;grabbed=false}
            }
        }
    }
}
