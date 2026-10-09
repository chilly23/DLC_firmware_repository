import QtQuick

Rectangle {
    id: tile
    width: 418; height: 80
    property bool mirrored: false
    property bool lower: false
    property bool editing: false
    property string fieldKey: "current"
    property real value: 0
    property int corner:-1
    property color tileInk:editing?theme.foreground:theme.parameterInk
    property color detailInk:editing?theme.foreground:theme.parameterDetailInk
    function formattedValue(){
        let s=Number(value).toFixed(spec.decimals)
        if(corner<0||navigation.editCorner!==corner)return s
        let power=navigation.digitPower,dot=s.indexOf(".");if(dot<0)dot=s.length
        let pos=power>=0?dot-power-1:dot-power
        if(pos<0||pos>=s.length)return s
        return s.slice(0,pos)+"<u>"+s[pos]+"</u>"+s.slice(pos+1)
    }
    property var spec: ctl.parameter(fieldKey)
    signal editRequested()
    signal moduleRequested()
    signal fieldRequested()
    color: editing ? theme.surface : theme.accent
    border.color: editing ? "#F0F0EB" : "transparent"
    border.width: editing ? 2 : 0
    onDetailInkChanged: dropdownArrow.requestPaint()
    Item {
        x: tile.mirrored ? 340 : 0; width: 78; height: 80; visible: !tile.editing
        Text { font.family:theme.fontFamily; x: 0; width:78; horizontalAlignment:Text.AlignHCenter; y: 10; text: tile.spec.module; color:tile.detailInk; font.pixelSize: theme.fontSize(20) }
        Icon { x: 24; y: 35; width: 30; height: 30; kind: tile.mirrored ? "chevronLeft" : "chevronRight"; ink:tile.detailInk }
        Rectangle { x: tile.mirrored ? 0 : 77; y: 11; width: 1; height: 60; color:tile.detailInk }
    }
    Text { font.family:theme.fontFamily;
        x: tile.mirrored ? 131 : 83; y: 9; width: 204; height: 58
        text:tile.formattedValue();textFormat:Text.RichText;color:tile.tileInk
         font.pixelSize: theme.fontSize(50); fontSizeMode: Text.Fit; minimumPixelSize: 30; horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
    Item {
        x: tile.mirrored ? 11 : 296; y: 0; width: 111; height: 80
        Text { font.family:theme.fontFamily; x: 0; y: 6; width: 111; height: 27; horizontalAlignment: tile.mirrored ? Text.AlignLeft : Text.AlignRight; text: theme.translate(theme.language,tile.spec.label); color:tile.detailInk; font.pixelSize: theme.fontSize(21); fontSizeMode: Text.Fit; minimumPixelSize: 14 }
        Rectangle { x: 0; y: 33; width: 111; height: 1; color:tile.detailInk }
        Canvas {
            id: dropdownArrow
            x: tile.mirrored ? 103 : 0; y: 33; width: 8; height: 8
            onPaint: {let c=getContext("2d");c.reset();c.fillStyle=tile.detailInk;c.beginPath();c.moveTo(0,0);c.lineTo(8,0);c.lineTo(4,7);c.closePath();c.fill()}
        }
        Text { font.family:theme.fontFamily; x: 0; y: 36; width: 103; text: tile.spec.unit; color:tile.detailInk; font.pixelSize: theme.fontSize(32); horizontalAlignment: tile.mirrored ? Text.AlignLeft : Text.AlignRight }
    }
    MouseArea { objectName: tile.objectName + "Value";property string navLabel:tile.spec.label+" value"; anchors.fill: parent; enabled: !tile.editing; onClicked: tile.editRequested() }
    MouseArea { objectName: tile.objectName + "Module";property string navLabel:"Select "+tile.spec.module+" module"; x: tile.mirrored ? 340 : 0; width: 78; height: 80; enabled: !tile.editing; onClicked: tile.moduleRequested() }
    MouseArea { objectName: tile.objectName + "Field";property string navLabel:"Choose parameter"; x: tile.mirrored ? 11 : 296; width: 111; height: 80; enabled: !tile.editing; onClicked: tile.fieldRequested() }
}
