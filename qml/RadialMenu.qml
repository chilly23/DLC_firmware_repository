import QtQuick

Item {
    id: menu
    z:20
    property int side: 0
    property int channelIndex: 0
    property real expansion: 0
    property real centerX: side===0 ? 63 : 1537
    property real centerY: 539
    property bool closing: false
    property string pendingOption: ""
    onVisibleChanged: if(!visible)ctl.setPresentationBusy(false)
    signal closed()
    signal chosen(string option, int channelIndex, int side)
    function open(paneSide, index) {
        side=paneSide; channelIndex=index; closing=false; pendingOption=""; expansion=0; visible=true; expand.from=0;expand.to=1;expand.restart()
    }
    function dismiss(option) {if(closing)return;closing=true;pendingOption=option||"";expand.stop();expand.from=expansion;expand.to=0;expand.start()}
    NumberAnimation {
        id: expand
        onRunningChanged:ctl.setPresentationBusy(running)
        onFinished:{if(menu.closing){menu.visible=false;if(menu.pendingOption!=="")menu.chosen(menu.pendingOption,menu.channelIndex,menu.side);else menu.closed()}}
        target:menu;property:"expansion";to:1;duration:220;easing.type:Easing.OutCubic
    }
    Rectangle { anchors.fill: parent; color: "#000000"; opacity: .77*menu.expansion }
    MouseArea { anchors.fill: parent; onClicked: menu.dismiss("") }
    Item {
        id: fan
        x: menu.centerX; y: menu.centerY
        scale: menu.expansion
        transformOrigin: Item.TopLeft
        Canvas {
            id: arcCanvas; layer.enabled:true;layer.smooth:true
            x: -360; y: -360; width: 720; height: 720
            onPaint: {
                let c=getContext("2d"); c.reset();c.translate(360,360)
                if(menu.side===1)c.scale(-1,1)
                c.beginPath(); c.arc(0,0,350,0,Math.PI*2)
                c.fillStyle="#000000";c.fill();c.lineWidth=2;c.strokeStyle="#D9D9D9";c.stroke()
                c.beginPath();c.arc(0,0,185,0,Math.PI*2);c.fillStyle="#0E140F";c.fill();c.stroke()
            }
            Connections { target: menu; function onSideChanged() { arcCanvas.requestPaint() } }
        }
        Repeater {
            model: [{name:"Alarms",icon:"alarm"},{name:"Settings",icon:"settings"},{name:"Display",icon:"display"},{name:"Diagnostics",icon:"diagnostics"}]
            Item {
                required property var modelData
                required property int index
                property string navLabel: modelData.name
                property real angle: (-100+(index+.5)*36.25)*Math.PI/180
                x: (menu.side===0?1:-1)*Math.cos(angle)*270-65
                y: Math.sin(angle)*270-48
                width: 130; height: 100
                Icon { x: 35; y: 0; width: 60; height: 60; kind: modelData.icon; ink: "#FFFFFF" }
                Text { font.family:theme.fontFamily; x: 0; y: 72; width: 130; horizontalAlignment: Text.AlignHCenter; text:theme.translate(theme.language,modelData.name); color: "#FFFFFF"; font.pixelSize: theme.fontSize(14) }
            }
        }
        MouseArea {
            objectName: "radialSectors"; x: -355; y: -355; width: 710; height: 710
            onClicked: function(mouse) {
                let dx=(mouse.x-355)*(menu.side===0?1:-1),dy=mouse.y-355
                let r=Math.sqrt(dx*dx+dy*dy),angle=Math.atan2(dy,dx)*180/Math.PI
                if(r<185 || r>350 || angle< -100 || angle>45) {menu.dismiss("");return}
                let i=Math.min(3,Math.floor((angle+100)/36.25))
                menu.dismiss(["Alarms","Settings","Display","Diagnostics"][i])
            }
        }
    }
    TouchButton {
        objectName: "radialCancel"; x: menu.centerX-50; y: menu.centerY-50; width: 100; height: 100; radius: 50
        normalColor: "#A92621"; iconName: "close"; ink: "#FFFFFF"; onClicked: menu.dismiss("")
    }
}
