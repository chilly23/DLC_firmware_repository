import QtQuick
import "Colors.js" as Colors

TouchButton {
    id: control
    property string label: ""
    property string symbol: ""
    property bool activeChoice: false
    normalColor: activeChoice ? Colors.activeButton : "#2B332D"
    ink: activeChoice ? Colors.activeInk : Colors.activeButton
    radius: 9
    border.width: activeChoice ? 0 : 1
    border.color: "#505B52"
    Row {
        anchors.centerIn: parent; spacing:12
        Icon {visible:control.symbol!=="";width:30;height:30;kind:control.symbol;ink:control.ink}
        Text {height:30;verticalAlignment:Text.AlignVCenter;text:control.label;color:control.ink;font.pixelSize:22}
    }
}
