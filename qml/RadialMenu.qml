import QtQuick
Item {
    id: menu
    z:20
    property int side:0
    property int channelIndex:0
    property real expansion:0
    property real position:0
    property real targetPosition:0
    property bool closing:false
    property string pendingOption:""
    property real centerX:side===0?0:1600
    property real centerY:720
    property var options:[{name:"Settings",label:"System settings",icon:"settings"},{name:"Display",label:"Display settings",icon:"display"},{name:"Alarms",label:"Alarms",icon:"alarm"},{name:"Diagnostics",label:"Control diagnostics",icon:"diagnostics"},{name:"Notifications",label:"Notifications",icon:"notifications"}]
    property int selectedIndex:((Math.round(position)%options.length)+options.length)%options.length
    signal closed()
    signal chosen(string option,int channelIndex,int side)
    function open(paneSide,index){side=paneSide;channelIndex=index;closing=false;pendingOption="";position=0;targetPosition=0;visible=true;reveal.to=1;reveal.restart()}
    function dismiss(option){if(closing)return;closing=true;pendingOption=option||"";reveal.to=0;reveal.restart()}
    function rotateSteps(delta){if(closing)return;targetPosition+=delta;spin.duration=210;spin.to=targetPosition;spin.restart()}
    function chooseCurrent(){if(!closing)dismiss(options[((Math.round(targetPosition)%options.length)+options.length)%options.length].name)}
    NumberAnimation {id:reveal;target:menu;property:"expansion";duration:720;easing.type:Easing.InOutCubic
        onFinished:if(menu.closing){menu.visible=false;if(menu.pendingOption)menu.chosen(menu.pendingOption,menu.channelIndex,menu.side);else menu.closed()}}
    NumberAnimation {id:spin;target:menu;property:"position";duration:210;easing.type:Easing.OutCubic}
    Rectangle {anchors.fill:parent;color:"#000000";opacity:.55*menu.expansion}
    MouseArea {anchors.fill:parent;onClicked:menu.dismiss("")}
    Item {
        id:fan;x:menu.centerX;y:menu.centerY;scale:menu.expansion;transformOrigin:Item.TopLeft
        Rectangle {
            x:menu.side===0?260:-596;y:-249;width:336;height:62;radius:10;color:theme.active
            Text {anchors.centerIn:parent;anchors.horizontalCenterOffset:menu.side===0?25:-25;width:265;elide:Text.ElideRight;horizontalAlignment:Text.AlignHCenter;text:theme.translate(theme.language,menu.options[menu.selectedIndex].label);font.family:theme.fontFamily;font.pixelSize:22;color:theme.activeInk}
        }
        Canvas {
            id:arcs;x:menu.side===0?0:-390;y:-390;width:390;height:390
            onPaint:{
                let c=getContext("2d");c.reset();c.translate(menu.side===0?0:390,390);if(menu.side===1)c.scale(-1,1)
                function sector(a,b,color){c.beginPath();c.arc(0,0,388,a,b);c.arc(0,0,188,b,a,true);c.closePath();c.fillStyle=color;c.fill()}
                sector(-Math.PI/2,0,theme.surface);sector(-Math.PI/3,-Math.PI/6,theme.active)
                c.lineWidth=1.5;c.strokeStyle=theme.muted
                for(let a of [-Math.PI/2,-Math.PI/3,-Math.PI/6,0]){c.beginPath();c.moveTo(Math.cos(a)*188,Math.sin(a)*188);c.lineTo(Math.cos(a)*388,Math.sin(a)*388);c.stroke()}
            }
            Connections {target:menu;function onSideChanged(){arcs.requestPaint()}}
            Connections {target:theme;function onChanged(){arcs.requestPaint()}}
        }
        Repeater {
            model:9
            Item {
                required property int index
                property real offset:index-4-(menu.position-Math.floor(menu.position))
                property int optionIndex:((Math.floor(menu.position)+index-4)%menu.options.length+menu.options.length)%menu.options.length
                property real angle:(-45+offset*30)*Math.PI/180
                x:(menu.side===0?1:-1)*Math.cos(angle)*285-34;y:Math.sin(angle)*285-34;width:68;height:68
                visible:Math.abs(offset)<1.49;opacity:Math.min(1,(1.49-Math.abs(offset))*3)
                Icon {anchors.fill:parent;kind:menu.options[parent.optionIndex].icon;ink:Math.abs(parent.offset)<.5?theme.activeInk:theme.foreground}
            }
        }
        MouseArea {
            objectName:"radialSectors";x:menu.side===0?0:-390;y:-390;width:390;height:390
            property real lastAngle:0;property bool dragged:false;property real velocity:0;property double lastTime:0
            function angleAt(mouse){let dx=menu.side===0?mouse.x:390-mouse.x;return Math.atan2(mouse.y-390,dx)*180/Math.PI}
            onPressed:function(mouse){spin.stop();lastAngle=angleAt(mouse);dragged=false;velocity=0;lastTime=Date.now()}
            onPositionChanged:function(mouse){if(!pressed)return;let now=Date.now(),a=angleAt(mouse),d=a-lastAngle;if(Math.abs(d)>.2){dragged=true;menu.position-=d/30;velocity=-d/Math.max(10,now-lastTime)*1000/30}lastAngle=a;lastTime=now}
            onReleased:function(mouse){
                if(dragged){menu.targetPosition=Math.round(menu.position+Math.max(-5,Math.min(5,velocity*.14)));spin.duration=450;spin.to=menu.targetPosition;spin.restart();return}
                let dx=menu.side===0?mouse.x:390-mouse.x,dy=mouse.y-390,r=Math.sqrt(dx*dx+dy*dy)
                if(r<188||r>390){menu.dismiss("");return}
                let slot=Math.round((angleAt(mouse)+45)/30)
                if(slot===0)menu.chooseCurrent();else menu.rotateSteps(slot)
            }
            onWheel:function(event){menu.rotateSteps(event.angleDelta.y<0?1:-1);event.accepted=true}
        }
    }
    TouchButton {objectName:"radialCancel";x:menu.side===0?20:1504;y:624;width:76;height:76;radius:38;normalColor:"#A92621";iconName:"close";ink:"#FFFFFF";onClicked:menu.dismiss("")}
}
