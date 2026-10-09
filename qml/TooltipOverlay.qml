import QtQuick

Item {
    id: tip
    objectName:"tooltipOverlay"
    visible:false
    property string heading:""
    property string body:""
    property real anchorX:0
    property real anchorY:0
    Connections {
        target:theme
        function onTipRequested(title,body,x,y){
            let p=tip.mapFromItem(null,x,y)
            tip.anchorX=p.x;tip.anchorY=p.y;tip.heading=title;tip.body=body
            tip.visible=true;expiry.restart()
        }
    }
    Timer {id:expiry;interval:5500;onTriggered:tip.visible=false}
    MouseArea {anchors.fill:parent;onPressed:function(mouse){tip.visible=false;mouse.accepted=true}}
    Rectangle {x:card.x+3;y:card.y+5;width:card.width;height:card.height;radius:14;color:"#40000000"}
    Rectangle {
        x:Math.max(card.x+22,Math.min(card.x+card.width-22,tip.anchorX))-8
        y:tip.anchorY>360?card.y+card.height-8:card.y-8
        width:16;height:16;rotation:45;color:card.color
    }
    Rectangle {
        id:card;width:390;height:145;radius:14
        x:Math.max(12,Math.min(1198,tip.anchorX-width/2))
        y:tip.anchorY>360?Math.max(10,tip.anchorY-height-18):Math.min(555,tip.anchorY+18)
        color:theme.light?"#FFFFFF":"#111827"
        Text {x:20;y:16;width:350;text:tip.heading;color:theme.light?"#111827":"#FFFFFF";font.family:theme.fontFamily;font.pixelSize:24;font.weight:Font.Medium}
        Text {x:20;y:52;width:350;height:82;text:tip.body;wrapMode:Text.WordWrap;color:theme.light?"#374151":"#D1D5DB";font.family:theme.fontFamily;font.pixelSize:18}
    }
}
