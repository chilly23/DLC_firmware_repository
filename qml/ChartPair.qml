import QtQuick

Item {
    id: pair
    property int channelIndex: 0
    property int revision: 0
    property string suffix: "0"
    property string mainObjectName: "absorption"+suffix
    property string errorObjectName: "error"+suffix
    property bool large: false
    property bool canMove: true
    property bool showLabels: true
    property bool labelOnRight: false
    property var chart: {revision;return ctl.channel(channelIndex).chart}
    property bool combined: chart.mode === "combined"
    property real gap: 18
    property real mainHeight: (height-gap)*chart.mainRatio
    property real errorHeight: height-gap-mainHeight
    signal signalsRequested()
    signal moveStarted(bool errorSignal, real x, real y)
    signal moveUpdated(real x, real y)
    signal moveFinished(real x, real y)
    signal moveCancelled()
    function viewRange() {return [main.xMinimum,main.xMaximum]}
    function setViewRange(lo,hi) {main.setRange(lo,hi)}
    // One gesture owner spans both traces, including the space between them.
    // It can take over single-finger panning or an already-started graph move.
    PinchHandler {
        id: pinch
        objectName: "chartPinch"+pair.suffix
        target: null
        minimumPointCount: 2
        maximumPointCount: 2
        grabPermissions: PointerHandler.CanTakeOverFromAnything
        rotationAxis.enabled: false
        onActiveChanged: if(active){main.cancelGesture();error.cancelGesture()}
        onScaleChanged: function(delta) {
            if(active && !main.interactionLocked)main.zoomAt(delta,centroid.position.x)
        }
    }
    function nudge(action,amount){
        if(action==="graph.reset"){main.resetView();error.resetView();return}
        if(action==="graph.zoom_in"||action==="graph.zoom_out"){main.zoomBy(Math.pow(1.12,(action==="graph.zoom_in"?1:-1)*amount));return}
        // Match a finger dragging the trace in the requested screen direction.
        let dx=action==="graph.left"?-24:action==="graph.right"?24:0
        let dy=action==="graph.up"?-18:action==="graph.down"?18:0
        main.panBy(dx*amount,dy*amount)
        if(!combined && dy)error.panBy(0,dy*amount)
    }
    PlotView {
        id: main; objectName: pair.mainObjectName
        width: parent.width; height: pair.combined ? pair.height : pair.mainHeight
        y: pair.combined || pair.chart.mainUpper ? 0 : pair.errorHeight+pair.gap
        channelIndex: pair.channelIndex; large: pair.large; canMove: pair.canMove;rightAxis:pair.labelOnRight
        combined: pair.combined; bottomAxis: pair.combined || !pair.chart.mainUpper
        onRangeChanged: function(lo,hi) {error.setRange(lo,hi)}
        onMoveStarted: function(x,y) {pair.moveStarted(false,x,y)}
        onMoveUpdated: function(x,y) {pair.moveUpdated(x,y)}
        onMoveFinished: function(x,y) {pair.moveFinished(x,y)}
        onMoveCancelled: pair.moveCancelled()
    }
    PlotView {
        id: error; objectName: pair.errorObjectName
        width: parent.width; height: pair.errorHeight
        y: pair.chart.mainUpper ? pair.mainHeight+pair.gap : 0
        visible: !pair.combined; errorPlot: true
        channelIndex: pair.channelIndex; large: pair.large; canMove: pair.canMove;rightAxis:pair.labelOnRight
        bottomAxis: pair.chart.mainUpper
        onRangeChanged: function(lo,hi) {main.setRange(lo,hi)}
        onMoveStarted: function(x,y) {pair.moveStarted(true,x,y)}
        onMoveUpdated: function(x,y) {pair.moveUpdated(x,y)}
        onMoveFinished: function(x,y) {pair.moveFinished(x,y)}
        onMoveCancelled: pair.moveCancelled()
    }
    // Both labels are one touch target, present on both panes and in fullscreen.
    Rectangle {
        width: pair.large ? 330 : 284; height: 42
        x: pair.large ? 70 : (pair.labelOnRight ? pair.width-width-59 : 59)
        y: 14
        property color labelSurface:theme.surface
        radius:5;color:Qt.rgba(labelSurface.r,labelSurface.g,labelSurface.b,.55);visible:pair.showLabels
        Row {
            anchors.centerIn: parent; spacing: 18
            Row {
                spacing: 7; opacity: !pair.combined || pair.chart.mainVisible ? 1 : .4
                Rectangle {y:11;width:24;height:1.7;color:theme.foreground}
                Text { font.family:theme.fontFamily;text:theme.translate(theme.language,"Spectroscopy");color:theme.foreground;font.pixelSize:(pair.large?20:17)*theme.textScale}
            }
            Row {
                spacing: 7; opacity: !pair.combined || pair.chart.errorVisible ? 1 : .4
                Row {y:11;spacing:2;Repeater {model:5;Rectangle {width:3;height:1.5;color:theme.foreground}}}
                Text { font.family:theme.fontFamily;text:theme.translate(theme.language,"Error");color:theme.foreground;font.pixelSize:(pair.large?20:17)*theme.textScale}
            }
        }
        MouseArea {objectName:"chartLabels"+pair.suffix;property string navLabel:"Chart signals";anchors.fill:parent;onClicked:pair.signalsRequested()}
    }
}
