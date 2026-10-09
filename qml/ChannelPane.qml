import QtQuick
import "Colors.js" as Colors

Item {
    id: pane
    width: 800; height: 720
    property int side: 0
    property int channelIndex: 0
    property int revision: 0
    property bool mirrored: side === 1
    property var channel: { revision; return ctl.channel(channelIndex) }
    property real idleOpacity: channel.emission ? 1 : Colors.idleOpacity
    Behavior on idleOpacity {NumberAnimation {duration:700;easing.type:Easing.InOutQuad}}
    signal editRequested(int channelIndex, string fieldKey, int side, bool bottom)
    signal fullscreenRequested(int side)
    signal moreRequested(int side)
    signal emissionRequested(int side,int channelIndex)
    signal notice(string message)
    signal selectorRequested(int index, string key, int side, bool bottom, bool modules)
    signal graphMoveStarted(int side, bool errorSignal, real x, real y)
    signal signalsRequested(int side, int index)
    signal graphMoveUpdated(real x, real y)
    signal graphMoveFinished(real x, real y)
    signal graphMoveCancelled()
    function viewRange() { return charts.viewRange() }
    function setViewRange(lo,hi) { charts.setViewRange(lo,hi) }
    function nudge(action,amount){charts.nudge(action,amount)}

    ParameterTile {
        objectName: "topParameter" + pane.side
        x: pane.mirrored ? 375 : 7; y: 7; mirrored: pane.mirrored
        fieldKey: pane.channel.top; value: pane.channel.values[fieldKey]
        corner:pane.side===0?0:2
        onEditRequested: pane.editRequested(pane.channelIndex, fieldKey, pane.side, false)
        onModuleRequested: pane.selectorRequested(pane.channelIndex, fieldKey, pane.side, false, true)
        onFieldRequested: pane.selectorRequested(pane.channelIndex, fieldKey, pane.side, false, false)
    }
    ParameterTile {
        objectName: "bottomParameter" + pane.side
        x: pane.mirrored ? 375 : 7; y: 634; mirrored: pane.mirrored; lower: true
        fieldKey: pane.channel.bottom; value: pane.channel.values[fieldKey]
        corner:pane.side===0?1:3
        onEditRequested: pane.editRequested(pane.channelIndex, fieldKey, pane.side, true)
        onModuleRequested: pane.selectorRequested(pane.channelIndex, fieldKey, pane.side, true, true)
        onFieldRequested: pane.selectorRequested(pane.channelIndex, fieldKey, pane.side, true, false)
    }
    Rectangle { opacity:pane.idleOpacity;x: pane.mirrored ? 33 : 765; y: 27; width: 6; height: 60; color: pane.channelIndex === 0 ? theme.laser1Color : theme.laser2Color }
    Text { font.family:theme.fontFamily; opacity:pane.idleOpacity;x: pane.mirrored ? 60 : 558; y: 27; width: 186; text: "Laser " + pane.channel.number; color: theme.foreground; font.pixelSize: theme.fontSize(24); horizontalAlignment: pane.mirrored ? Text.AlignLeft : Text.AlignRight }
    Text { font.family:theme.fontFamily; objectName:"channelStatus"+pane.side;x: pane.mirrored ? 60 : 490; y: 69; width: 254; text: pane.channel.status; color: pane.channel.emission?theme.foreground:"#7E877F";font.pixelSize: theme.fontSize(16); horizontalAlignment: pane.mirrored ? Text.AlignLeft : Text.AlignRight;Behavior on color {ColorAnimation {duration:700}} }
    TouchButton { opacity:pane.idleOpacity;objectName: "switch" + pane.side; x: pane.mirrored ? 318 : 428; y: 2; width: 50; height: 44; iconName: "switch"; iconSize: 32; onClicked: ctl.switchView(pane.side) }
    TouchButton { opacity:pane.idleOpacity;objectName: "fullscreen" + pane.side; x: pane.mirrored ? 318 : 428; y: 48; width: 50; height: 47; iconName: "fullscreen"; iconSize: 32; onClicked: pane.fullscreenRequested(pane.side) }
    ChartPair {
        id: charts; objectName: "charts" + pane.side
        opacity:pane.idleOpacity
        x: pane.mirrored ? 15 : 122; y: 100; width: 680; height: 511
        channelIndex: pane.channelIndex; revision: pane.revision; suffix: String(pane.side)
        labelOnRight: pane.side === 1
        onSignalsRequested: pane.signalsRequested(pane.side,pane.channelIndex)
        onMoveStarted: function(errorSignal,x,y) {pane.graphMoveStarted(pane.side,errorSignal,x,y)}
        onMoveUpdated: function(x,y) {pane.graphMoveUpdated(x,y)}
        onMoveFinished: function(x,y) {pane.graphMoveFinished(x,y)}
        onMoveCancelled: pane.graphMoveCancelled()
    }
    Rectangle { opacity:pane.idleOpacity;x: pane.mirrored ? 697 : 105; y: 111; width: 5; height: 494; color: pane.channelIndex === 0 ? theme.laser1Color : theme.laser2Color }
    TouchButton {
        objectName: "lock" + pane.side; caption:theme.buttonLabels?theme.translate(theme.language,"Lock") : ""; x: pane.mirrored ? 705 : 7; y: 124; width: 88; height: 90; radius: 24
        opacity:pane.idleOpacity
        iconName: pane.channel.locked ? "lock" : "unlock"; iconSize: 64; ink: pane.channel.locked ? theme.activeInk : theme.foreground; normalColor: pane.channel.locked ? theme.active : "transparent"; selected: pane.channel.locked
        onClicked: ctl.toggleLock(pane.channelIndex)
    }
    TouchButton {
        objectName: "emission" + pane.side; caption:theme.buttonLabels?theme.translate(theme.language,"Emission") : ""; x: pane.mirrored ? 705 : 7; y: 230; width: 88; height: 86; radius: 24
        iconName: "emission"; iconSize: 64; ink: pane.channel.emission ? theme.activeInk : theme.foreground; normalColor: pane.channel.emission ? theme.active : "transparent"
        onClicked: pane.emissionRequested(pane.side,pane.channelIndex)
    }
    TouchButton {
        objectName: "stabilise" + pane.side; caption:theme.buttonLabels?theme.translate(theme.language,"Stabilise") : ""; x: pane.mirrored ? 705 : 7; y: 323; width: 88; height: 88; radius: 24
        opacity:pane.idleOpacity
        iconName: "stabilise"; iconSize: 64; ink: pane.channel.stabilised ? theme.activeInk : theme.foreground; normalColor: pane.channel.stabilised ? theme.active : "transparent"
        onClicked: ctl.toggleStabilisation(pane.channelIndex)
    }
    TouchButton {
        objectName: "shortcut" + pane.side; x: pane.mirrored ? 705 : 7; y: 430; width: 88; height: 85
        opacity:pane.idleOpacity
        iconName:"";text:theme.translate(theme.language,ctl.shortcutLabel(pane.side));textSize:16;ink:theme.muted;normalColor:"transparent"
        onClicked: ctl.runShortcut(pane.side)
    }
    TouchButton {
        objectName: "more" + pane.side; caption:theme.buttonLabels?theme.translate(theme.language,"More") : ""; x: pane.mirrored ? 705 : 7; y: 526; width: 88; height: 78
        opacity:pane.idleOpacity
        iconName: "more"; iconSize: 64; onClicked: pane.moreRequested(pane.side)
    }
}
