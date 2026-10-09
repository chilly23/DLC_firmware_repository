import QtQuick

Item {
    id: guide
    objectName:"tourOverlay"
    visible:systemSettings.tourIndex>=0 && !info.section
    property var info:systemSettings.tour
    property real fx:info.rect[0]
    property real fy:info.rect[1]
    property real fw:info.rect[2]
    property real fh:info.rect[3]
    Behavior on fx {NumberAnimation{duration:350;easing.type:Easing.InOutCubic}}
    Behavior on fy {NumberAnimation{duration:350;easing.type:Easing.InOutCubic}}
    Behavior on fw {NumberAnimation{duration:350;easing.type:Easing.InOutCubic}}
    Behavior on fh {NumberAnimation{duration:350;easing.type:Easing.InOutCubic}}
    Rectangle {x:0;y:0;width:1600;height:Math.max(0,guide.fy);color:"#73000000"}
    Rectangle {x:0;y:guide.fy+guide.fh;width:1600;height:Math.max(0,720-y);color:"#73000000"}
    Rectangle {x:0;y:guide.fy;width:guide.fx;height:guide.fh;color:"#73000000"}
    Rectangle {x:guide.fx+guide.fw;y:guide.fy;width:Math.max(0,1600-x);height:guide.fh;color:"#73000000"}
    Rectangle {x:guide.fx;y:guide.fy;width:guide.fw;height:guide.fh;color:"transparent";border.color:theme.accent;border.width:3;radius:10}
    MouseArea {anchors.fill:parent}
    Rectangle {
        id:card;x:guide.fx>=800?24:830;y:guide.fy>500?260:484;width:740;height:218;radius:18;color:theme.surface
        Behavior on x {NumberAnimation{duration:300}}
        Text {x:24;y:14;width:parent.width-48;text:(systemSettings.tourIndex+1)+" / "+guide.info.count+"    "+guide.info.title;color:theme.foreground;font.family:theme.fontFamily;font.pixelSize:24;font.weight:Font.Medium}
        Text {x:24;y:60;width:parent.width-48;height:76;wrapMode:Text.WordWrap;text:guide.info.body;color:theme.foreground;font.family:theme.fontFamily;font.pixelSize:18}
        Row {x:24;y:154;spacing:12
            TouchButton {objectName:"tourSkip";width:158;height:48;radius:8;normalColor:theme.raised;text:theme.translate(theme.language,"Skip guide");textSize:20;onClicked:systemSettings.stopTour()}
            TouchButton {objectName:"tourPause";width:110;height:48;radius:8;normalColor:theme.raised;text:theme.translate(theme.language,systemSettings.tourPlaying?"Pause":"Play");textSize:20;onClicked:systemSettings.tourPause()}
            TouchButton {objectName:"tourPrevious";width:170;height:48;radius:8;normalColor:theme.raised;text:theme.translate(theme.language,"Previous");textSize:20;onClicked:systemSettings.tourPrevious()}
            TouchButton {objectName:"tourNext";width:170;height:48;radius:8;normalColor:theme.accent;ink:theme.accentInk;text:theme.translate(theme.language,"Next");textSize:20;onClicked:systemSettings.tourNext()}
        }
    }
}
