import QtQuick

Item {
    Text {text:"Host and application runtime · updates once per second while this page is open";font.family:theme.fontFamily;font.pixelSize:22;color:theme.muted}
    Grid {y:52;columns:4;spacing:16
        Repeater {model:workspace.metrics
            Rectangle {
                required property var modelData
                width:364;height:145;color:theme.light?"#D7DAD7":"#282828"
                Text {x:20;y:16;width:324;text:modelData.name;font.family:theme.fontFamily;font.pixelSize:19;color:theme.muted}
                Text {x:20;y:53;width:324;height:78;text:modelData.value;font.family:theme.fontFamily;font.pixelSize:26;color:theme.foreground;wrapMode:Text.WordWrap;elide:Text.ElideRight}
            }
        }
    }
}
