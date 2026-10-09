import QtQuick

Rectangle {
    id: control
    property string navLabel:"Chart height ratio"
    property string navKind:"slider"
    function stepFromKnob(delta){moved(Math.max(minimum,Math.min(maximum,value+delta)))}
    property real value: 50
    property real minimum: 0
    property real maximum: 100
    property string suffix: "%"
    signal moved(real value)
    color: theme.raised; radius: 7
    border.width: 1; border.color: theme.muted
    property real tileWidth: Math.min(100, width*.265)
    property real travel: width-tileWidth-8
    Rectangle {
        id: tile
        x: 4+(control.value-control.minimum)/(control.maximum-control.minimum)*control.travel
        y:4;width:control.tileWidth;height:parent.height-8;radius:5
        color:theme.accent;border.color:theme.muted;border.width:1
        Text {anchors.centerIn:parent;text:Math.round(control.value)+control.suffix;color:theme.accentInk;font.family:theme.fontFamily;font.pixelSize:theme.fontSize(24)}
    }
    MouseArea {
        anchors.fill:parent
        property real grab:0
        function apply(x){control.moved(control.minimum+Math.max(0,Math.min(1,(x-4-grab)/control.travel))*(control.maximum-control.minimum))}
        onPressed:function(mouse){grab=mouse.x>=tile.x&&mouse.x<=tile.x+tile.width?mouse.x-tile.x:tile.width/2;apply(mouse.x)}
        onPositionChanged:function(mouse){if(pressed)apply(mouse.x)}
    }
}
