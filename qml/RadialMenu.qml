import QtQuick

Item {
    id: menu
    property int side: 0
    property int channelIndex: 0
    property real expansion: 0
    property real centerX: side===0 ? 63 : 1537
    property real centerY: 539
    property bool animating: expand.running
    property bool closing: false
    property string pendingOption: ""
    property int transitionMs: 800
    onAnimatingChanged: ctl.setPresentationBusy(animating)
    signal closed()
    signal chosen(string option, int channelIndex, int side)
    function open(paneSide, index) {
        expand.stop();ctl.setPresentationBusy(true);side=paneSide;channelIndex=index;closing=false;pendingOption="";expansion=0;visible=true;arcCanvas.requestPaint()
        Qt.callLater(function(){if(menu.visible&&!menu.closing)menu.animateTo(1)})
    }
    function animateTo(value) {expand.stop();expand.from=expansion;expand.to=value;expand.duration=Math.max(120,transitionMs*Math.abs(value-expansion));expand.start()}
    function requestClose(option) {
        if(closing || !visible)return
        closing=true;pendingOption=option||"";animateTo(0)
    }
    NumberAnimation { id: expand; target: menu; property: "expansion";duration:800;easing.type:Easing.InOutCubic
        onFinished: {
            if(menu.closing) {
                let option=menu.pendingOption;menu.visible=false
                if(option!=="")menu.chosen(option,menu.channelIndex,menu.side)
                else menu.closed()
            }
        }
    }
    onVisibleChanged: if(!visible){expand.stop();ctl.setPresentationBusy(false)}
    Rectangle { anchors.fill: parent; color: "#000000"; opacity: .77*menu.expansion }
    MouseArea { anchors.fill: parent; onClicked: menu.requestClose("") }
    Item {
        id: fan
        objectName:"radialFan"
        x: menu.centerX-360; y: menu.centerY-360;width:720;height:720
        scale: .14+.86*menu.expansion
        transformOrigin: Item.Center
        layer.enabled: true
        layer.smooth: true
        Canvas {
            id: arcCanvas
            x: 0; y: 0; width: 720; height: 720
            onPaint: {
                let c=getContext("2d"); c.reset();c.translate(360,360)
                if(menu.side===1)c.scale(-1,1)
                c.fillStyle="#000000";c.lineWidth=2;c.strokeStyle="#D9D9D9"
                for(let i=0;i<4;i++) {
                    let a=(-100+i*36.25)*Math.PI/180,b=(-100+(i+1)*36.25)*Math.PI/180
                    c.beginPath();c.arc(0,0,350,a,b);c.lineTo(Math.cos(b)*185,Math.sin(b)*185)
                    c.arc(0,0,185,b,a,true);c.closePath();c.fill();c.stroke()
                }
            }
            Connections { target: menu; function onSideChanged() { arcCanvas.requestPaint() } }
        }
        Repeater {
            model: [{name:"Signals",icon:"signals"},{name:"Settings",icon:"settings"},{name:"Display",icon:"display"},{name:"Diagnostics",icon:"diagnostics"}]
            Item {
                required property var modelData
                required property int index
                property real angle: (-100+(index+.5)*36.25)*Math.PI/180
                x: 360+(menu.side===0?1:-1)*Math.cos(angle)*270-65
                y: 360+Math.sin(angle)*270-48
                width: 130; height: 100
                Icon { x: 35; y: 0; width: 60; height: 60; kind: modelData.icon; ink: "#FFFFFF" }
                Text { x: 0; y: 72; width: 130; horizontalAlignment: Text.AlignHCenter; text: modelData.name; color: "#FFFFFF"; font.pixelSize: 14 }
            }
        }
        MouseArea {
            objectName: "radialSectors"; x: 5; y: 5; width: 710; height: 710
            enabled: !menu.animating
            onClicked: function(mouse) {
                let dx=(mouse.x-355)*(menu.side===0?1:-1),dy=mouse.y-355
                let r=Math.sqrt(dx*dx+dy*dy),angle=Math.atan2(dy,dx)*180/Math.PI
                if(r<185 || r>350 || angle< -100 || angle>45) {menu.requestClose("");return}
                let i=Math.min(3,Math.floor((angle+100)/36.25))
                menu.requestClose(["Signals","Settings","Display","Diagnostics"][i])
            }
        }
    }
    TouchButton {
        objectName: "radialCancel"; x: menu.centerX-50; y: menu.centerY-50; width: 100; height: 100; radius: 50
        normalColor: "#A92621"; iconName: "close"; ink: "#FFFFFF"; onClicked: menu.requestClose("")
    }
}
