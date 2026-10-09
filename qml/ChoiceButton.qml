import QtQuick
import "Colors.js" as Colors

TouchButton {
    id: control
    property string label: ""
    property string symbol: ""
    property bool activeChoice: false
    navLabel:label
    tipInfo:theme.tipFor(symbol)
    normalColor: activeChoice ? theme.active : (theme.light ? "#E3E3E3" : "#2B2B2B")
    ink: activeChoice ? "#111111" : theme.foreground
    radius: 12
    border.width: 1
    border.color: activeChoice ? theme.active : (theme.light ? "#AAAAAA" : "#515151")
    Rectangle {
        anchors.fill: parent; anchors.margins: 3; radius: 9
        color: activeChoice ? theme.active : "transparent"
        opacity: activeChoice ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } }
    }
    Row {
        anchors.centerIn: parent; spacing:12
        Icon {visible:control.symbol!=="";width:30;height:30;kind:control.symbol;ink:control.ink}
        Text { font.family:theme.fontFamily;height:30;verticalAlignment:Text.AlignVCenter;text:theme.translate(theme.language,control.label);color:control.ink;font.pixelSize: theme.fontSize(22)}
    }
}
