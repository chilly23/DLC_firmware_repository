import QtQuick

Item {
    id:root
    property int revision:0
    signal editRequested(int index,string key)
    Connections {target:parameters;function onChanged(){root.revision++}}
    Connections {target:ctl;function onChanged(){root.revision++}}
    Text {text:"Assign a parameter, then tap its value to edit.";font.family:theme.fontFamily;font.pixelSize:23;color:theme.muted}
    Grid {y:51;columns:2;spacing:20
        Repeater {model:4
            Rectangle {
                id:corner;required property int index
                property int side:index%2
                property bool lower:index>=2
                property int channelIndex:side===0?ctl.leftChannel:ctl.rightChannel
                property var channel:{root.revision;return ctl.channel(channelIndex)}
                property string field:lower?channel.bottom:channel.top
                width:742;height:204;color:theme.light?"#D7DAD7":"#272727"
                Text {x:20;y:14;text:(corner.side===0?"Top / bottom left":"Top / bottom right").replace("Top / bottom",corner.lower?"Bottom":"Top")+" · Laser "+(corner.channelIndex+1);font.family:theme.fontFamily;font.pixelSize:21;color:theme.muted}
                LobbyChoice {
                    objectName:"homeAssignment"+corner.index;x:20;y:48;width:702;height:48
                    model:parameters.fields;textRole:"name";valueRole:"key"
                    currentIndex:parameters.fields.findIndex(item=>item.key===corner.field)
                    navLabel:"Choose "+(corner.side===0?"left":"right")+" "+(corner.lower?"bottom":"top")+" parameter"
                    onActivated:function(index){ctl.selectField(corner.channelIndex,corner.lower,parameters.fields[index].key)}
                }
                Text {x:20;y:118;width:570;text:{root.revision;let spec=ctl.parameter(corner.field);return Number(ctl.value(corner.channelIndex,corner.field)).toFixed(spec.decimals)+" "+spec.unit} font.family:theme.fontFamily;font.pixelSize:42;color:theme.foreground;elide:Text.ElideRight}
                LobbyButton {objectName:"homeEdit"+corner.index;x:610;y:119;width:112;height:58;text:"Edit";onClicked:root.editRequested(corner.channelIndex,corner.field)}
                MouseArea {x:16;y:112;width:580;height:74;onClicked:root.editRequested(corner.channelIndex,corner.field)}
            }
        }
    }
    Text {y:485;width:1150;text:"Assignments follow each laser. When both panels show the same laser, their assignments stay linked.";font.family:theme.fontFamily;font.pixelSize:18;color:theme.muted;wrapMode:Text.WordWrap}
    LobbyButton {x:1210;y:478;width:294;height:44;text:theme.buttonLabels?"Side icons + names":"Side icons only";onClicked:workspace.toggleButtonLabels()}
}
