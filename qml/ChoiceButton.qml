import QtQuick

TouchButton {
    id: control
    property string label: ""
    property string symbol: ""
    property bool activeChoice: false
    normalColor: activeChoice ? "#D9D9D9" : "#2B332D"
    ink: activeChoice ? "#101610" : "#E9ECE8"
    radius: 9
    border.width: activeChoice ? 0 : 1
    border.color: "#505B52"
    Row {
        anchors.centerIn: parent; spacing:12
        Icon {visible:control.symbol!=="";width:30;height:30;kind:control.symbol;ink:control.ink}
        Text {height:30;verticalAlignment:Text.AlignVCenter;text:control.label;color:control.ink;font.pixelSize:22}
    }
}
