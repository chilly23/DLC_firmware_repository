import QtQuick

Rectangle {
    id: button
    property string iconName: ""
    property bool mirrorIcon: false
    property string text: ""
    property string caption: ""
    property color ink: theme.foreground
    property color normalColor: "transparent"
    property bool selected: false
    property int iconSize: 52
    property int textSize: 24
    signal clicked()
    signal held()
    property bool holdEnabled: false
    property bool navEnabled:true
    property string navLabel:caption||text||iconName
    property var tipInfo:theme.tipFor(iconName)
    property string tipTitle:tipInfo.title
    property string tipBody:tipInfo.body
    color: pointer.pressed ? theme.raised : normalColor
    Accessible.role: Accessible.Button
    Accessible.name: text !== "" ? text : iconName
    Icon { id:glyph;anchors.centerIn: parent; anchors.verticalCenterOffset:button.caption!==""?-11:0; width: Math.min(button.width-10,button.iconSize*theme.uiScale)*(button.caption!==""?.72:1); height: width; visible: button.iconName !== ""; kind: button.iconName; ink: button.ink; active: button.selected
        transform:Scale {origin.x:glyph.width/2;xScale:button.mirrorIcon?-1:1}
    }
    Text { font.family:theme.fontFamily; anchors.centerIn: parent; text: button.text; visible: button.text !== ""; color: button.ink; font.pixelSize: theme.fontSize(button.textSize); width:parent.width-8;horizontalAlignment:Text.AlignHCenter;fontSizeMode:Text.Fit;minimumPixelSize:14 }
    Text {font.family:theme.fontFamily;anchors.bottom:parent.bottom;anchors.bottomMargin:7;width:parent.width;horizontalAlignment:Text.AlignHCenter;text:button.caption;visible:text!=="";font.pixelSize:16*theme.fontScale;color:button.ink;fontSizeMode:Text.Fit;minimumPixelSize:11}
    MouseArea {
        id:pointer;objectName:button.objectName+"Pointer";anchors.fill:parent
        property bool holdConsumed:false
        property double pressedAt:0
        function consumeHold(){
            if(holdConsumed||!containsMouse)return
            holdConsumed=true
            if(button.holdEnabled)button.held()
            else if(button.tipTitle!==""){let p=button.mapToItem(null,button.width/2,button.height/2);theme.showTip(button.tipTitle,button.tipBody,p.x,p.y)}
        }
        onPressed:{holdConsumed=false;pressedAt=Date.now();if(button.holdEnabled||button.tipTitle!=="")holdTimer.restart()}
        onReleased:{if(pressedAt>0 && Date.now()-pressedAt>=holdTimer.interval && (button.holdEnabled||button.tipTitle!==""))consumeHold();holdTimer.stop();pressedAt=0}
        onCanceled:{holdTimer.stop();holdConsumed=false;pressedAt=0}
        onExited:{holdTimer.stop();pressedAt=0}
        onClicked:if(!holdConsumed)button.clicked()
        Timer {id:holdTimer;interval:button.holdEnabled?650:850;onTriggered:if(pointer.pressed)pointer.consumeHold()}
    }
}
