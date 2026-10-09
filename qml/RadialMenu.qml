import QtQuick

Item {
    id:menu;z:20
    property int side:0
    property int channelIndex:0
    property real expansion:0
    property real centerX:side===0?63:1537
    property real centerY:555
    property bool closing:false
    property bool animating:expand.running
    property string pendingOption:""
    property int targetPosition:0
    property int selectedIndex:((targetPosition%4)+4)%4
    property var options:[{name:"Alarms",icon:"alarm"},{name:"Settings",icon:"settings"},{name:"Display",icon:"display"},{name:"Diagnostics",icon:"diagnostics"}]
    signal closed()
    signal chosen(string option,int channelIndex,int side)
    function animateTo(value){expand.stop();expand.from=expansion;expand.to=value;expand.duration=Math.max(120,800*Math.abs(value-expansion));expand.start()}
    function open(paneSide,index){
        expand.stop();side=paneSide;channelIndex=index;targetPosition=0;closing=false;pendingOption="";expansion=0;visible=true
        ctl.setPresentationBusy(true);arcCanvas.requestPaint()
        Qt.callLater(function(){if(menu.visible&&!menu.closing)menu.animateTo(1)})
    }
    function dismiss(option){if(closing||!visible)return;closing=true;pendingOption=option||"";animateTo(0)}
    function rotateSteps(amount){if(!closing){targetPosition+=amount;arcCanvas.requestPaint()}}
    function chooseCurrent(){if(!closing)dismiss(options[selectedIndex].name)}
    NumberAnimation {
        id:expand;target:menu;property:"expansion";duration:800;easing.type:Easing.InOutCubic
        onRunningChanged:ctl.setPresentationBusy(running)
        onFinished:if(menu.closing){let option=menu.pendingOption;menu.visible=false;if(option)menu.chosen(option,menu.channelIndex,menu.side);else menu.closed()}
    }
    onVisibleChanged:if(!visible){expand.stop();ctl.setPresentationBusy(false)}
    Rectangle {anchors.fill:parent;color:"#000000";opacity:.77*menu.expansion}
    MouseArea {anchors.fill:parent;onClicked:menu.dismiss("")}
    Item {
        id:fan;objectName:"radialFan"
        x:menu.centerX-360;y:menu.centerY-360;width:720;height:720
        scale:.14+.86*menu.expansion;transformOrigin:Item.Center
        layer.enabled:true;layer.smooth:true
        Canvas {
            id:arcCanvas;width:720;height:720
            onPaint:{
                let c=getContext("2d");c.reset();c.translate(360,360);if(menu.side===1)c.scale(-1,1)
                c.lineWidth=2;c.strokeStyle="#D9D9D9"
                for(let i=0;i<4;i++){
                    let a=(-100+i*36.25)*Math.PI/180,b=(-100+(i+1)*36.25)*Math.PI/180
                    c.beginPath();c.arc(0,0,350,a,b);c.arc(0,0,185,b,a,true);c.closePath()
                    c.fillStyle=i===menu.selectedIndex?"#D9D9D9":"#000000";c.fill();c.stroke()
                }
            }
            Connections {target:menu;function onSideChanged(){arcCanvas.requestPaint()} function onSelectedIndexChanged(){arcCanvas.requestPaint()}}
        }
        Repeater {
            model:menu.options
            Item {
                required property int index
                required property var modelData
                property real angle:(-100+(index+.5)*36.25)*Math.PI/180
                property color ink:index===menu.selectedIndex?"#111111":"#FFFFFF"
                x:360+(menu.side===0?1:-1)*Math.cos(angle)*270-65
                y:360+Math.sin(angle)*270-48;width:130;height:92
                Icon {x:38;y:0;width:54;height:54;kind:parent.modelData.icon;ink:parent.ink}
                Text {x:0;y:60;width:130;height:24;horizontalAlignment:Text.AlignHCenter;text:theme.translate(theme.language,parent.modelData.name);color:parent.ink;font.family:theme.fontFamily;font.pixelSize:18;elide:Text.ElideRight}
            }
        }
        MouseArea {
            objectName:"radialSectors";x:5;y:5;width:710;height:710;enabled:!menu.animating
            onClicked:function(mouse){
                let dx=(mouse.x-355)*(menu.side===0?1:-1),dy=mouse.y-355
                let r=Math.sqrt(dx*dx+dy*dy),angle=Math.atan2(dy,dx)*180/Math.PI
                if(r<185||r>350||angle< -100||angle>45){menu.dismiss("");return}
                let i=Math.min(3,Math.floor((angle+100)/36.25));menu.targetPosition=i;menu.chooseCurrent()
            }
            onWheel:function(event){menu.rotateSteps(event.angleDelta.y<0?1:-1);event.accepted=true}
        }
    }
    TouchButton {objectName:"radialCancel";x:menu.centerX-50;y:menu.centerY-50;width:100;height:100;radius:50;normalColor:"#A92621";iconName:"close";ink:"#FFFFFF";onClicked:menu.dismiss("")}
}
