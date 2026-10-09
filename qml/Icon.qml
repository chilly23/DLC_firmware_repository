import QtQuick

Canvas {
    id: icon
    property string kind: "lock"
    property color ink: "#D9D9D9"
    property bool active: false
    onKindChanged: requestPaint()
    onInkChanged: requestPaint()
    onActiveChanged: requestPaint()
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onAvailableChanged: if(available) requestPaint()
    onVisibleChanged: if(visible) requestPaint()
    onPaint: {
        let c = getContext("2d"); c.reset();
        c.scale(width/64, height/64); c.strokeStyle=ink; c.fillStyle=ink;
        c.lineWidth=2.2; c.lineCap="round"; c.lineJoin="round";
        function line(points) {c.beginPath(); c.moveTo(points[0][0],points[0][1]); for(let i=1;i<points.length;i++) c.lineTo(points[i][0],points[i][1]); c.stroke()}
        if(kind === "more") {for(let x of [14,32,50]) {c.beginPath();c.arc(x,32,3,0,Math.PI*2);c.fill()} }
        else if(kind === "close") {line([[21,21],[43,43]]);line([[43,21],[21,43]])}
        else if(kind === "fullscreen") {
            for(let p of [[[10,25],[10,10],[25,10]],[[39,10],[54,10],[54,25]],[[54,39],[54,54],[39,54]],[[25,54],[10,54],[10,39]]])line(p)
        } else if(kind === "switch") {
            line([[18,21],[10,21],[10,48],[54,48],[54,21],[39,21]]);line([[37,10],[26,21],[37,31]]);line([[26,21],[46,21]])
        } else if(kind === "target") {
            line([[24,7],[24,57]]); for(let y of [14,29,44])line([[6,y],[24,y]]);
            line([[34,32],[59,32]]);line([[46,19],[59,32],[46,45]])
        } else if(kind === "display") {
            c.strokeRect(5,10,54,36);line([[32,46],[32,56]]);line([[20,56],[44,56]])
        } else if(kind === "settings") {
            let points=[]; for(let i=0;i<32;i++){let a=i*Math.PI/16;let r=(i%4===0||i%4===3)?27:21;points.push([32+Math.cos(a)*r,32+Math.sin(a)*r])}points.push(points[0]);line(points);c.beginPath();c.arc(32,32,10,0,Math.PI*2);c.stroke()
        } else if(kind === "signals" || kind === "stabilise") {
            c.beginPath();c.moveTo(3,32);c.lineTo(10,32);c.bezierCurveTo(22,32,18,8,27,12);c.bezierCurveTo(36,16,31,53,42,49);c.bezierCurveTo(49,46,46,31,61,32);c.stroke();
            if(kind === "stabilise") {c.fillStyle=ink.toString()==="#101610"?"#BDC0BB":"#0E140F";c.fillRect(37,30,24,28);c.strokeStyle=ink;c.strokeRect(38,39,21,21);c.beginPath();c.arc(48.5,39,7,Math.PI,0);c.stroke();line([[49,47],[49,53]])}
        } else if(kind === "drag") {
            c.strokeRect(6,25,28,30);c.setLineDash([4,4]);c.strokeRect(25,5,28,30);c.setLineDash([]);
            line([[38,17],[55,17]]);line([[47,8],[47,26]]);
            line([[32,49],[28,42],[30,39],[36,43],[41,54],[42,45],[46,45],[49,49],[51,48],[56,54],[60,62],[48,64],[39,60],[31,58]])
        } else if(kind === "diagnostics") {line([[3,33],[18,33],[26,8],[37,56],[44,23],[49,33],[61,33]])}
        else if(kind === "backspace") {line([[22,18],[55,18],[55,46],[22,46],[7,32],[22,18]]);line([[31,25],[44,39]]);line([[44,25],[31,39]])}
        else if(kind === "enter") {line([[50,14],[50,37],[13,37]]);line([[26,25],[13,37],[26,48]])}
        else if(kind === "left") {line([[49,32],[15,32]]);line([[27,20],[15,32],[27,44]])}
        else if(kind === "right") {line([[15,32],[49,32]]);line([[37,20],[49,32],[37,44]])}
        else {
            c.beginPath();c.roundedRect(12,26,40,34,5,5);c.stroke();
            c.beginPath(); if(active) {c.arc(32,24,12,Math.PI,0)} else {c.arc(32,24,12,Math.PI,0);c.lineTo(44,26)} c.stroke();line([[32,39],[32,47]])
        }
    }
}
