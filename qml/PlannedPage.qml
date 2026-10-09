import QtQuick

Rectangle {
    property string title
    property string glyph
    property string detail
    color:theme.light?"#D7DAD7":"#272727"
    Icon {x:48;y:54;width:72;height:72;kind:parent.glyph;ink:theme.muted}
    Text {x:48;y:165;text:parent.title;font.family:theme.fontFamily;font.pixelSize:38;color:theme.foreground}
    Text {x:48;y:231;width:1100;text:parent.detail;font.family:theme.fontFamily;font.pixelSize:25;color:theme.muted;wrapMode:Text.WordWrap}
    Text {x:48;y:parent.height-67;text:"Reserved for a future release";font.family:theme.fontFamily;font.pixelSize:20;color:theme.muted}
}
