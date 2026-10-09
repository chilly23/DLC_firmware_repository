import QtQuick
import Nexatom 1.0

Item {
    id: view
    property int channelIndex: 0
    property bool errorPlot: false
    property bool large: false
    property bool canMove: true
    property bool combined: false
    property bool bottomAxis: errorPlot
    property alias interactionLocked: plot.interactionLocked
    property alias xMinimum: plot.xMinimum
    property alias xMaximum: plot.xMaximum
    signal rangeChanged(real minimum, real maximum)
    signal moveStarted(real x, real y)
    signal moveUpdated(real x, real y)
    signal moveFinished(real x, real y)
    signal moveCancelled()
    function setRange(lo, hi) { plot.setRange(lo, hi) }
    function resetView() { plot.resetView() }
    SpectrumPlot {
        id: plot; anchors.fill: parent; objectName: view.objectName + "Renderer"
        channelIndex: view.channelIndex; errorPlot: view.errorPlot; large: view.large
        combined: view.combined; bottomAxis: view.bottomAxis
        onChanged: view.rangeChanged(xMinimum, xMaximum)
    }
    PinchArea {
        anchors.fill: parent
        enabled: !view.interactionLocked
        property real previousScale: 1
        onPinchStarted: { previousScale = 1; pointer.cancelHold() }
        onPinchUpdated: function(event) {
            plot.zoom(event.scale / previousScale, event.center.x)
            previousScale = event.scale
        }
        MouseArea {
            id: pointer; objectName: view.objectName + "Pointer"
            anchors.fill: parent
            preventStealing: draggingPanel
            property bool draggingPanel: false
            function cancelHold() {hold.stop();if(draggingPanel)view.moveCancelled();draggingPanel=false;moved=true}
            function globalPoint(x,y) {return mapToItem(null,x,y)}
            property real lastX: 0
            property real lastY: 0
            property real startX: 0
            property real startY: 0
            property bool moved: false
            onPressed: function(mouse) { lastX=mouse.x; lastY=mouse.y; startX=mouse.x; startY=mouse.y; moved=false;draggingPanel=false;if(view.canMove)hold.restart() }
            onPositionChanged: function(mouse) {
                if(!pressed) return
                if(draggingPanel) {let p=globalPoint(mouse.x,mouse.y);view.moveUpdated(p.x,p.y);lastX=mouse.x;lastY=mouse.y;return}
                if(Math.abs(mouse.x-startX)+Math.abs(mouse.y-startY)>8) moved=true
                if(moved) hold.stop()
                if(moved) plot.pan(mouse.x-lastX, mouse.y-lastY)
                lastX=mouse.x;lastY=mouse.y
            }
            onReleased: function(mouse) { hold.stop();if(draggingPanel){let p=globalPoint(mouse.x,mouse.y);view.moveFinished(p.x,p.y)}else if(!moved && !view.errorPlot) plot.pick(mouse.x);draggingPanel=false }
            onCanceled: cancelHold()
            onDoubleClicked: {plot.resetView();if(view.canMove)hold.restart()}
            onWheel: function(wheel) { plot.zoom(wheel.angleDelta.y>0 ? 1.15 : 1/1.15, wheel.x); wheel.accepted=true }
            Timer {id:hold;interval:550;onTriggered:{if(pointer.pressed&&!pointer.moved&&!view.interactionLocked){pointer.draggingPanel=true;let p=pointer.globalPoint(pointer.lastX,pointer.lastY);view.moveStarted(p.x,p.y)}}}
        }
    }
    Connections {target: plot;function onChanged(){if(view.interactionLocked)pointer.cancelHold()}}
}
