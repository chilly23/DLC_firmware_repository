import QtQuick
Rectangle {
    id:toast
    property var entry:notifications.toast
    visible:entry.text!==""
    x:438;y:630;width:724;height:78;radius:12;z:70
    color:theme.surface
    property color levelColor:entry.level==="critical"?"#FF453A":entry.level==="warning"?"#FFD60A":theme.foreground
    Rectangle {width:4;height:parent.height-22;x:0;y:11;radius:2;color:toast.levelColor}
    Canvas {id:severity;x:15;y:24;width:30;height:30
        onPaint:{let c=getContext("2d");c.reset();c.strokeStyle=toast.levelColor;c.fillStyle=toast.levelColor;c.lineWidth=2
            if(toast.entry.level==="warning"){c.beginPath();c.moveTo(15,2);c.lineTo(29,27);c.lineTo(1,27);c.closePath();c.stroke();c.fillRect(14,10,2,8);c.fillRect(14,21,2,2)}
            else {c.beginPath();c.arc(15,15,12,0,Math.PI*2);c.stroke();c.fillRect(14,8,2,11);c.fillRect(14,22,2,2)}}
        Connections {target:notifications;function onChanged(){severity.requestPaint()}}
    }
    Text {x:56;y:10;width:toast.entry.decision?430:602;height:58;wrapMode:Text.WordWrap;verticalAlignment:Text.AlignVCenter;maximumLineCount:2;elide:Text.ElideRight;text:toast.entry.text;font.family:theme.fontFamily;font.pixelSize:20;color:theme.foreground}
    TouchButton {x:505;y:15;width:130;height:48;visible:toast.entry.decision;navLabel:"Confirm notification";text:"Confirm";normalColor:theme.active;ink:theme.activeInk;onClicked:notifications.accept()}
    TouchButton {x:658;y:10;width:56;height:58;navLabel:"Dismiss notification";iconName:"close";iconSize:24;onClicked:notifications.dismiss()}
}
