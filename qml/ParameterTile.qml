import QtQuick

Rectangle {
    id: tile
    width: 418; height: 80
    property bool mirrored: false
    property bool lower: false
    property bool editing: false
    property string fieldKey: "current"
    property real value: 0
    property var spec: ctl.parameter(fieldKey)
    signal editRequested()
    signal moduleRequested()
    signal fieldRequested()
    color: editing ? "#000000" : "#008622"
    border.color: editing ? "#F0F0EB" : "transparent"
    border.width: editing ? 2 : 0
    Item {
        x: tile.mirrored ? 337 : 0; width: 78; height: 80; visible: !tile.editing
        Text { x: 26; y: 10; text: tile.spec.module; color: "white"; font.pixelSize: 20 }
        Text { x: 30; y: 34; text: tile.mirrored ? "<" : ">"; color: "white"; font.pixelSize: 32 }
        Rectangle { x: tile.mirrored ? 0 : 77; y: 11; width: 1; height: 60; color: "#B6D2B9" }
    }
    Text {
        x: tile.mirrored ? 158 : 83; y: 9; width: tile.mirrored ? 176 : 204; height: 58
        text: Number(tile.value).toFixed(tile.spec.decimals); color: "#EFF0EB"
        font.family: "Roboto"; font.pixelSize: 50; fontSizeMode: Text.Fit; minimumPixelSize: 30; horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
    Item {
        x: tile.mirrored ? 28 : 296; y: 0; width: 111; height: 80
        Text { x: 0; y: 6; width: 111; height: 27; horizontalAlignment: tile.mirrored ? Text.AlignLeft : Text.AlignRight; text: tile.spec.label; color: "#FFFFFF"; font.pixelSize: 21; fontSizeMode: Text.Fit; minimumPixelSize: 14 }
        Rectangle { x: 0; y: 33; width: 111; height: 1; color: "#F0F0EB" }
        Canvas {
            x: tile.mirrored ? 103 : 0; y: 33; width: 8; height: 8
            onPaint: {let c=getContext("2d");c.reset();c.fillStyle="#FFFFFF";c.beginPath();c.moveTo(0,0);c.lineTo(8,0);c.lineTo(4,7);c.closePath();c.fill()}
        }
        Text { x: 0; y: 36; width: 103; text: tile.spec.unit; color: "#FFFFFF"; font.pixelSize: 32; horizontalAlignment: tile.mirrored ? Text.AlignLeft : Text.AlignRight }
    }
    MouseArea { objectName: tile.objectName + "Value"; anchors.fill: parent; enabled: !tile.editing; onClicked: tile.editRequested() }
    MouseArea { objectName: tile.objectName + "Module"; x: tile.mirrored ? 337 : 0; width: 78; height: 80; enabled: !tile.editing; onClicked: tile.moduleRequested() }
    MouseArea { objectName: tile.objectName + "Field"; x: tile.mirrored ? 28 : 296; width: 111; height: 80; enabled: !tile.editing; onClicked: tile.fieldRequested() }
}
