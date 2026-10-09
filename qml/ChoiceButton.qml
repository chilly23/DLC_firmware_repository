import QtQuick
import "Colors.js" as Colors

TouchButton {
    id: control
    property string label: ""
    property string symbol: ""
    property bool activeChoice: false
    tipInfo:theme.tipFor(symbol)
    normalColor: activeChoice ? theme.accent : theme.raised
    ink: activeChoice ? theme.accentInk : theme.foreground
    radius: 12
    border.width: 1
    border.color: activeChoice ? theme.accent : "#505B52"
    Rectangle {
        anchors.fill: parent; anchors.margins: 3; radius: 9
        color: activeChoice ? theme.accent : "transparent"
        opacity: activeChoice ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
    }
    Row {
        anchors.centerIn: parent; spacing:12
        Icon {visible:control.symbol!=="";width:30;height:30;kind:control.symbol;ink:control.ink}
        Text { font.family:theme.fontFamily;height:30;verticalAlignment:Text.AlignVCenter;text:theme.translate(theme.language,control.label);color:control.ink;font.pixelSize: theme.fontSize(22)}
    }
}
