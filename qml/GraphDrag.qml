import QtQuick

Item {
    id: drag
    property int sourceSide: 0
    property int channelIndex: 0
    property real pointerX: 0
    property real pointerY: 0
    property real anchorX: 0
    property real anchorY: 0
    property int revision: 0
    property var leftData: {
        revision;
        return ctl.channel(ctl.leftChannel);
    }
    property var rightData: {
        revision;
        return ctl.channel(ctl.rightChannel);
    }
    property int targetSide: pointerX < 800 ? 0 : 1
    function begin(side, index, x, y) {
        sourceSide = side;
        channelIndex = index;
        pointerX = anchorX = x;
        pointerY = anchorY = y;
        visible = true;
    }
    function move(x, y) {
        pointerX = x;
        pointerY = y;
    }
    function finish(x, y) {
        move(x, y);
        if (y >= 100 && y <= 617 && x >= 103 && x <= 1503)
            ctl.moveGraph(sourceSide, targetSide);
        visible = false;
    }
    Rectangle {
        anchors.fill: parent
        color: "#0E140F"
    }
    ParameterTile {
        x: 7
        y: 7
        fieldKey: drag.leftData.top
        value: drag.leftData.values[fieldKey]
        enabled: false
    }
    ParameterTile {
        x: 7
        y: 634
        fieldKey: drag.leftData.bottom
        value: drag.leftData.values[fieldKey]
        lower: true
        enabled: false
    }
    ParameterTile {
        x: 1175
        y: 7
        fieldKey: drag.rightData.top
        value: drag.rightData.values[fieldKey]
        mirrored: true
        enabled: false
    }
    ParameterTile {
        x: 1175
        y: 634
        fieldKey: drag.rightData.bottom
        value: drag.rightData.values[fieldKey]
        mirrored: true
        lower: true
        enabled: false
    }
    Repeater {
        model: [
            {
                x: 536,
                y: 21,
                w: 240,
                h: 76
            },
            {
                x: 829,
                y: 21,
                w: 240,
                h: 76
            },
            {
                x: 0,
                y: 113,
                w: 96,
                h: 464
            },
            {
                x: 1511,
                y: 113,
                w: 89,
                h: 464
            }
        ]
        Rectangle {
            required property var modelData
            x: modelData.x
            y: modelData.y
            width: modelData.w
            height: modelData.h
            radius: 20
            color: "#404040"
        }
    }
    Repeater {
        model: 2
        Rectangle {
            required property int index
            x: index === 0 ? 104 : 827
            y: 111
            width: 675
            height: 466
            radius: 20
            color: "#404040"
            border.width: drag.targetSide === index ? 2 : 0
            border.color: "#D9D9D9"
            Icon {
                anchors.horizontalCenter: parent.horizontalCenter
                y: 143
                width: 132
                height: 132
                kind: "drag"
                ink: "#BFC2BE"
            }
            Text {
                anchors.horizontalCenter: parent.horizontalCenter
                y: 304
                text: "Drag & drop"
                font.pixelSize: 18
                color: "#BFC2BE"
            }
        }
    }
    Rectangle {
        x: Math.max(103, Math.min(840, (drag.sourceSide === 0 ? 122 : 815) + drag.pointerX - drag.anchorX))
        y: Math.max(105, Math.min(155, 110 + drag.pointerY - drag.anchorY))
        width: 750
        height: 539
        radius: 0
        color: "#101411"
        border.width: 1
        border.color: "#71766F"
        PlotView {
            x: 0
            y: 0
            width: 750
            height: 358
            channelIndex: drag.channelIndex
            canMove: false
            enabled: false
        }
        PlotView {
            x: 0
            y: 358
            width: 750
            height: 181
            errorPlot: true
            channelIndex: drag.channelIndex
            canMove: false
            enabled: false
        }
    }
}
