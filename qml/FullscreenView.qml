import QtQuick

Rectangle {
    id: full
    color: "#0E140F"
    property int channelIndex: 0
    property int revision: 0
    property var channel: { revision; return ctl.channel(channelIndex) }
    signal closed()
    signal signalsRequested()
    function viewRange() { return charts.viewRange() }
    function setViewRange(lo,hi) { charts.setViewRange(lo,hi) }
    Text { x: 27; y: 21; text: "Laser " + full.channel.number; font.pixelSize: 30; color: "#E5E7E2" }
    Rectangle { x: 178; y: 16; width: 2; height: 47; color: "#D9D9D9" }
    Text { x: 214; y: 24; text: full.channel.status.replace(";", " ·"); font.pixelSize: 26; color: "#D9D9D9" }
    TouchButton {
        objectName: "exitFullscreen"; x: 1330; y: 10; width: 246; height: 57; radius: 6; border.width: 1; border.color: "#D9D9D9"
        Icon { x: 13; y: 13; width: 32; height: 32; kind: "fullscreen" }
        Text { x: 60; y: 13; text: "Exit fullscreen"; color: "#D9D9D9"; font.pixelSize: 24 }
        onClicked: full.closed()
    }
    ChartPair {id:charts;x:19;y:90;width:1564;height:603;large:true;canMove:false;channelIndex:full.channelIndex;revision:full.revision;suffix:"Fullscreen";mainObjectName:"fullscreenAbsorption";errorObjectName:"fullscreenError";onSignalsRequested:full.signalsRequested()}
    Text { x: 1440; y: 691; text: "Piezo (V)"; font.pixelSize: 22; color: "#D9D9D9" }
}
