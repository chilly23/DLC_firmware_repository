import QtQuick

TouchButton {
    id: control
    property string label: ""
    property string symbol: ""
    property bool activeChoice: false
    tipInfo:theme.tipFor(symbol)
    normalColor:theme.raised;radius:12
    Text {x:20;anchors.verticalCenter:parent.verticalCenter;text:theme.translate(theme.language,control.label);color:theme.foreground;font.family:theme.fontFamily;font.pixelSize:theme.fontSize(24)}
    Rectangle {
        x:parent.width-106;y:(parent.height-44)/2;width:82;height:44;radius:22
        color:control.activeChoice?theme.accent:theme.muted
        Behavior on color {ColorAnimation {duration:180}}
        Rectangle {
            x:control.activeChoice?42:4;y:4;width:36;height:36;radius:18;color:"#FFFFFF"
            Behavior on x {NumberAnimation {duration:180;easing.type:Easing.OutCubic}}
        }
    }
}
