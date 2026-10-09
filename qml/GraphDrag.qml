import QtQuick

Item {
    id: drag
    property int sourceSide: 0
    property int channelIndex: 0
    property bool errorSignal: false
    property var sourceChart: {revision;return ctl.channel(channelIndex).chart}
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
    property bool wholeChannel: targetSide !== sourceSide || sourceChart.mode === "combined"
    property real upperHeight: 493*(sourceChart.mainUpper ? sourceChart.mainRatio : 1-sourceChart.mainRatio)
    property bool targetUpper: pointerY < 100+upperHeight+9
    property bool sourceUpper: errorSignal ? !sourceChart.mainUpper : sourceChart.mainUpper
    property bool destinationLocked: (targetSide === 0 ? leftData : rightData).locked
    property bool validDrop: (targetSide===0?pointerX>=122&&pointerX<=778:pointerX>=822&&pointerX<=1478) && pointerY >= 100 && pointerY <= 611 && !destinationLocked
    function begin(side, index, error, x, y) {
        sourceSide = side;
        channelIndex = index;
        errorSignal = error;
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
        if (validDrop) {
            if (targetSide !== sourceSide) ctl.moveGraph(sourceSide,targetSide)
            else if (!wholeChannel && targetUpper !== sourceUpper) ctl.swapLocal(channelIndex)
        }
        visible = false;
    }
    Rectangle {
        anchors.fill: parent
        color: theme.background
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
                x: 824,
                y: 21,
                w: 240,
                h: 76
            },
            {
                x: 7,
                y: 113,
                w: 88,
                h: 464
            },
            {
                x: 1505,
                y: 113,
                w: 88,
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
            color: theme.raised
        }
    }
    Repeater {
        model: 2
        Rectangle {
            required property int index
            objectName:"dropPanel"+index
            x: index === 0 ? 122 : 822; y:100; width:656;height:511
            radius:12;color:theme.surface
            border.width: drag.wholeChannel && drag.targetSide===index ? 2 : 0
            border.color: drag.destinationLocked ? "#A92621" : theme.foreground
            property int paneSide: index
            property var paneChart: (index===0?drag.leftData:drag.rightData).chart
            property real paneUpperHeight: 493*(paneChart.mainUpper?paneChart.mainRatio:1-paneChart.mainRatio)
            Repeater {
                model: parent.paneChart.mode==="combined"?1:2
                Rectangle {
                    required property int index
                    property bool highlighted:!drag.wholeChannel && parent.paneSide===drag.sourceSide && (index===0)===drag.targetUpper
                    property color itemInk:highlighted?theme.activeInk:theme.foreground
                    x:8;y:index===0?8:parent.paneUpperHeight+18
                    width:parent.width-16;height:parent.paneChart.mode==="combined"?495:index===0?parent.paneUpperHeight-8:493-parent.paneUpperHeight-8
                    radius:8
                    color:highlighted?theme.active:theme.raised
                    border.width:highlighted?2:0
                    border.color:theme.foreground
                    Column {
                        anchors.centerIn:parent;spacing:2
                        Image {objectName:"dropArtwork";anchors.horizontalCenter:parent.horizontalCenter;width:Math.min(100,parent.parent.height-37);height:width;source:"image://outline/drag/"+parent.parent.itemInk.toString().replace("#","");fillMode:Image.PreserveAspectFit;smooth:true}
                        Text { font.family:theme.fontFamily;anchors.horizontalCenter:parent.horizontalCenter;text:parent.parent.parent.paneChart.mode==="combined"?"Combined":index===0?"Upper":"Lower";font.pixelSize: theme.fontSize(20);color:parent.parent.itemInk}
                    }
                }
            }
        }
    }
    Rectangle {
        x: Math.max(122, Math.min(1478-width, (drag.sourceSide === 0 ? 135 : 835) + drag.pointerX - drag.anchorX))
        y: Math.max(102, Math.min(610-height, (drag.sourceUpper?110:118+drag.upperHeight) + drag.pointerY - drag.anchorY))
        width: 630
        height: drag.wholeChannel ? 475 : Math.max(100,493*(drag.errorSignal?1-drag.sourceChart.mainRatio:drag.sourceChart.mainRatio)-12)
        radius: 0
        color: theme.surface
        border.width: 1
        border.color: "#71766F"
        opacity: .88
        ChartPair {anchors.fill:parent;visible:drag.wholeChannel;channelIndex:drag.channelIndex;revision:drag.revision;suffix:"Drag";canMove:false;showLabels:false;enabled:false;labelOnRight:drag.sourceSide===1}
        PlotView {
            anchors.fill:parent;visible:!drag.wholeChannel
            errorPlot: drag.errorSignal;bottomAxis:true
            rightAxis:drag.sourceSide===1
            channelIndex: drag.channelIndex
            canMove: false
            enabled: false
        }
    }
    Text { font.family:theme.fontFamily;x:435;y:649;width:730;height:40;horizontalAlignment:Text.AlignHCenter;font.pixelSize: theme.fontSize(21);color:theme.foreground;text:drag.destinationLocked?"Destination graph is locked":!drag.validDrop?"Release outside to cancel":drag.wholeChannel?"Move both signals with Laser "+(drag.channelIndex+1):"Move "+(drag.errorSignal?"Error":"Spectroscopy")+" · "+(drag.targetUpper?"Upper":"Lower")}
}
