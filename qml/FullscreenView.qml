import QtQuick
import "Colors.js" as Colors

Rectangle {
    id: full
    color: theme.background
    property int channelIndex: 0
    property int revision: 0
    property var channel: { revision; return ctl.channel(channelIndex) }
    property real idleOpacity: channel.emission?1:Colors.idleOpacity
    Behavior on idleOpacity {NumberAnimation {duration:700;easing.type:Easing.InOutQuad}}
    signal closed()
    signal signalsRequested()
    function viewRange() { return charts.viewRange() }
    function setViewRange(lo,hi) { charts.setViewRange(lo,hi) }
    function nudge(action,amount) { charts.nudge(action,amount) }
    Text { font.family:theme.fontFamily; opacity:full.idleOpacity;x: 27; y: 21; text: "Laser " + full.channel.number; font.pixelSize: theme.fontSize(30); color: theme.foreground }
    Rectangle { x: 178; y: 16; width: 2; height: 47; color: theme.foreground }
    Text { font.family:theme.fontFamily; x: 214; y: 24; text: full.channel.status.replace(";", " ·"); font.pixelSize: theme.fontSize(26); color: full.channel.emission?theme.foreground:"#7E877F" }
    TouchButton {
        objectName: "exitFullscreen"; navLabel:"Exit fullscreen"; x: 1330; y: 10; width: 246; height: 57; radius: 6; border.width: 1; border.color: theme.foreground
        Icon { x: 13; y: 13; width: 32; height: 32; kind: "fullscreen" }
        Text { font.family:theme.fontFamily; x: 60; y: 13; text:theme.translate(theme.language,"Exit fullscreen"); color: theme.foreground; font.pixelSize: theme.fontSize(24) }
        onClicked: full.closed()
    }
    ChartPair {id:charts;opacity:full.idleOpacity;x:19;y:90;width:1564;height:603;large:true;canMove:false;channelIndex:full.channelIndex;revision:full.revision;suffix:"Fullscreen";mainObjectName:"fullscreenAbsorption";errorObjectName:"fullscreenError";onSignalsRequested:full.signalsRequested()}
    Text { font.family:theme.fontFamily; x: 1440; y: 691; text: "Piezo (V)"; font.pixelSize: theme.fontSize(22); color: theme.foreground }
}
