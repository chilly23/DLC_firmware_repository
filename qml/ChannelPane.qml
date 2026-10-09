import QtQuick

Item {
    id: pane
    width: 800; height: 720
    property int side: 0
    property int channelIndex: 0
    property int revision: 0
    property bool mirrored: side === 1
    property var channel: { revision; return ctl.channel(channelIndex) }
    signal editRequested(int channelIndex, string fieldKey, int side, bool bottom)
    signal fullscreenRequested(int side)
    signal moreRequested(int side)
    signal notice(string message)
    signal selectorRequested(int index, string key, int side, bool bottom, bool modules)
    signal graphMoveStarted(int side, bool errorSignal, real x, real y)
    signal signalsRequested(int side, int index)
    signal graphMoveUpdated(real x, real y)
    signal graphMoveFinished(real x, real y)
    signal graphMoveCancelled()
    function viewRange() { return charts.viewRange() }
    function setViewRange(lo,hi) { charts.setViewRange(lo,hi) }

    ParameterTile {
        objectName: "topParameter" + pane.side
        x: pane.mirrored ? 375 : 7; y: 7; mirrored: pane.mirrored
        fieldKey: pane.channel.top; value: pane.channel.values[fieldKey]
        onEditRequested: pane.editRequested(pane.channelIndex, fieldKey, pane.side, false)
        onModuleRequested: pane.selectorRequested(pane.channelIndex, fieldKey, pane.side, false, true)
        onFieldRequested: pane.selectorRequested(pane.channelIndex, fieldKey, pane.side, false, false)
    }
    ParameterTile {
        objectName: "bottomParameter" + pane.side
        x: pane.mirrored ? 375 : 7; y: 634; mirrored: pane.mirrored; lower: true
        fieldKey: pane.channel.bottom; value: pane.channel.values[fieldKey]
        onEditRequested: pane.editRequested(pane.channelIndex, fieldKey, pane.side, true)
        onModuleRequested: pane.selectorRequested(pane.channelIndex, fieldKey, pane.side, true, true)
        onFieldRequested: pane.selectorRequested(pane.channelIndex, fieldKey, pane.side, true, false)
    }
    Rectangle { x: pane.mirrored ? 33 : 765; y: 27; width: 6; height: 60; color: pane.channelIndex === 0 ? "#D9D9D9" : "#2362E5" }
    Text { x: pane.mirrored ? 60 : 558; y: 27; width: 186; text: "Laser " + pane.channel.number; color: "#FFFFFF"; font.pixelSize: 24; horizontalAlignment: pane.mirrored ? Text.AlignLeft : Text.AlignRight }
    Text { x: pane.mirrored ? 60 : 490; y: 69; width: 254; text: pane.channel.status; color: "#FFFFFF"; font.pixelSize: 16; horizontalAlignment: pane.mirrored ? Text.AlignLeft : Text.AlignRight }
    TouchButton { objectName: "switch" + pane.side; x: pane.mirrored ? 318 : 428; y: 2; width: 50; height: 44; iconName: "switch"; iconSize: 32; onClicked: ctl.switchView(pane.side) }
    TouchButton { objectName: "fullscreen" + pane.side; x: pane.mirrored ? 318 : 428; y: 48; width: 50; height: 47; iconName: "fullscreen"; iconSize: 32; onClicked: pane.fullscreenRequested(pane.side) }
    ChartPair {
        id: charts; objectName: "charts" + pane.side
        x: pane.mirrored ? 15 : 122; y: 100; width: 680; height: 511
        channelIndex: pane.channelIndex; revision: pane.revision; suffix: String(pane.side)
        onSignalsRequested: pane.signalsRequested(pane.side,pane.channelIndex)
        onMoveStarted: function(errorSignal,x,y) {pane.graphMoveStarted(pane.side,errorSignal,x,y)}
        onMoveUpdated: function(x,y) {pane.graphMoveUpdated(x,y)}
        onMoveFinished: function(x,y) {pane.graphMoveFinished(x,y)}
        onMoveCancelled: pane.graphMoveCancelled()
    }
    Rectangle { x: pane.mirrored ? 697 : 105; y: 111; width: 5; height: 494; color: pane.channelIndex === 0 ? "#A7AAA5" : "#2362E5" }
    TouchButton {
        objectName: "lock" + pane.side; x: pane.mirrored ? 711 : -1; y: 124; width: 96; height: 90; radius: 24
        iconName: pane.channel.locked ? "lock" : "unlock"; iconSize: 64; ink: pane.channel.locked ? "#101610" : "#F0F1EE"; normalColor: pane.channel.locked ? "#BDC0BB" : "transparent"; selected: pane.channel.locked
        onClicked: ctl.toggleLock(pane.channelIndex)
    }
    TouchButton {
        objectName: "emission" + pane.side; x: pane.mirrored ? 711 : -1; y: 230; width: 96; height: 86; radius: 24
        iconName: "emission"; iconSize: 64; ink: pane.channel.emission ? "#101610" : "#F0F1EE"; normalColor: pane.channel.emission ? "#BDC0BB" : "transparent"
        onClicked: ctl.toggleEmission(pane.channelIndex)
    }
    TouchButton {
        objectName: "stabilise" + pane.side; x: pane.mirrored ? 711 : -1; y: 323; width: 96; height: 88; radius: 24
        iconName: "stabilise"; iconSize: 64; ink: pane.channel.stabilised ? "#101610" : "#F0F1EE"; normalColor: pane.channel.stabilised ? "#BDC0BB" : "transparent"
        onClicked: ctl.toggleStabilisation(pane.channelIndex)
    }
    TouchButton {
        objectName: "shortcut" + pane.side; x: pane.mirrored ? 712 : 0; y: 430; width: 96; height: 85
        text: "Not\nSet"
        onClicked: pane.notice("Shortcut not set")
    }
    TouchButton {
        objectName: "more" + pane.side; x: pane.mirrored ? 712 : 0; y: 526; width: 96; height: 78
        iconName: "more"; iconSize: 64; onClicked: pane.moreRequested(pane.side)
    }
}
