import QtQuick
import QtQuick.Controls

Button {
    id: control
    property string navLabel: text
    property string glyph: ""
    property bool emphasized: false
    implicitWidth: 180; implicitHeight: 56
    font.family: theme.fontFamily
    Accessible.name: text
    background: Rectangle {
        radius: 0
        color: control.down ? "#525252" : control.emphasized ? "#D9D9D9" : theme.light ? "#D8DAD8" : "#2C2C2C"
        border.width: control.activeFocus ? 2 : 0
        border.color: theme.foreground
    }
    contentItem: Item {
        Icon { visible: control.glyph!=="";x:control.text===""?(parent.width-width)/2:10;anchors.verticalCenter:parent.verticalCenter;width:26;height:26;kind:control.glyph;ink:control.emphasized?"#111111":theme.foreground }
        Text { anchors.fill:parent;anchors.leftMargin:control.glyph!==""?48:10;anchors.rightMargin:10;text:control.text;font.family:theme.fontFamily;font.pixelSize:19;horizontalAlignment:Text.AlignHCenter;verticalAlignment:Text.AlignVCenter;elide:Text.ElideRight;color:control.emphasized?"#111111":theme.foreground }
    }
}
