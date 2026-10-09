import QtQuick
import Nexatom 1.0

Item {
    id: view
    property int channelIndex: 0
    property bool errorPlot: false
    property bool large: false
    property alias xMinimum: plot.xMinimum
    property alias xMaximum: plot.xMaximum
    signal rangeChanged(real minimum, real maximum)
    function setRange(lo, hi) { plot.setRange(lo, hi) }
    function resetView() { plot.resetView() }
    SpectrumPlot {
        id: plot; anchors.fill: parent; objectName: view.objectName + "Renderer"
        channelIndex: view.channelIndex; errorPlot: view.errorPlot; large: view.large
        onChanged: view.rangeChanged(xMinimum, xMaximum)
    }
    PinchArea {
        anchors.fill: parent
        property real previousScale: 1
        onPinchStarted: previousScale = 1
        onPinchUpdated: function(event) {
            plot.zoom(event.scale / previousScale, event.center.x)
            previousScale = event.scale
        }
        MouseArea {
            anchors.fill: parent
            property real lastX: 0
            property real lastY: 0
            property real startX: 0
            property real startY: 0
            property bool moved: false
            onPressed: function(mouse) { lastX=mouse.x; lastY=mouse.y; startX=mouse.x; startY=mouse.y; moved=false }
            onPositionChanged: function(mouse) {
                if(!pressed) return
                if(Math.abs(mouse.x-startX)+Math.abs(mouse.y-startY)>8) moved=true
                if(moved) plot.pan(mouse.x-lastX, mouse.y-lastY)
                lastX=mouse.x;lastY=mouse.y
            }
            onReleased: function(mouse) { if(!moved && !view.errorPlot) plot.pick(mouse.x) }
            onDoubleClicked: plot.resetView()
            onWheel: function(wheel) { plot.zoom(wheel.angleDelta.y>0 ? 1.15 : 1/1.15, wheel.x); wheel.accepted=true }
        }
    }
}
