import QtQuick
Item {
    id:stack
    x:438;y:0;width:724;height:708;z:notifications.toast.decision?70:19
    visible:cards.count>0
    property int appearanceRevision:0
    Connections {target:theme;function onChanged(){stack.appearanceRevision++}}
    Repeater {
        id:cards;model:notifications.model
        delegate:Item {
            id:card
            required property int index
            required property int noticeId
            required property string text
            required property string level
            required property bool decision
            required property real alpha
            required property int blurStep
            required property int revision
            objectName:"noticeCard"+noticeId
            width:724;height:78
            y:708-78-(cards.count-1-index)*88
            opacity:alpha
            Behavior on y {NumberAnimation {duration:190;easing.type:Easing.OutCubic}}
            Image {
                anchors.fill:parent;cache:false;smooth:true
                source:"image://notices/"+card.noticeId+"/"+card.blurStep+"/"+card.revision+"/"+stack.appearanceRevision
            }
            MouseArea {
                anchors.fill:parent
                onWheel:function(wheel){wheel.accepted=true}
            }
            MouseArea {
                x:505;y:15;width:130;height:48;visible:card.decision;enabled:card.blurStep===0
                property string navLabel:"Confirm notification: "+card.text
                onClicked:notifications.acceptId(card.noticeId)
            }
            MouseArea {
                x:658;y:10;width:56;height:58
                property string navLabel:"Dismiss notification: "+card.text
                onClicked:notifications.dismissId(card.noticeId)
            }
        }
    }
}
