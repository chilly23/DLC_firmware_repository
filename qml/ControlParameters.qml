import QtQuick
import QtQuick.Controls

Item {
    id: root
    property int channelIndex:0
    property int revision:0
    signal editRequested(int index,string key)
    signal emissionRequested(int index)
    Connections { target:parameters; function onChanged(){root.revision++} }
    Row { spacing:8
        Repeater {model:2
            LobbyButton {required property int index;objectName:"controlLaser"+index;width:170;height:44;text:"Laser "+(index+1);emphasized:root.channelIndex===index;onClicked:root.channelIndex=index}
        }
    }
    Text {x:490;y:10;text:"Live application values · simulated readbacks";font.family:theme.fontFamily;font.pixelSize:19;color:theme.muted}
    Row {y:58;spacing:24
        Repeater {model:2
            Item {
                id: column
                required property int index
                property string module:index===0?"CC":"TC"
                width:740;height:464
                Rectangle {width:740;height:44;color:theme.light?"#CED1CE":"#323232"}
                Text {x:16;y:8;text:column.module==="CC"?"Current Control":column.module==="TC"?"Temperature Control":"Piezo Control";font.family:theme.fontFamily;font.pixelSize:23;color:theme.foreground}
                LobbyChoice {objectName:"controlModule"+column.index;x:554;y:0;width:186;height:44;model:["CC","TC","PC"];currentIndex:model.indexOf(column.module);navLabel:"Control module "+(column.index+1);onActivated:function(index){column.module=model[index]}}
                ListView {
                    y:48;width:740;height:416;clip:true;boundsBehavior:Flickable.StopAtBounds
                    model:{root.revision;return parameters.controlRows(root.channelIndex,column.module).length}
                    ScrollBar.vertical:ScrollBar {}
                    delegate:ParameterRow {
                        required property int index
                        property var modelData:{root.revision;return parameters.controlRows(root.channelIndex,column.module)[index] || parameters.treeRows("")[0]}
                        objectName:"control_"+column.index+"_"+modelData.key
                        width:740;entry:modelData;channelIndex:root.channelIndex
                        onEditRequested:function(index,key){root.editRequested(index,key)}
                        onEmissionRequested:function(index){root.emissionRequested(index)}
                    }
                }
            }
        }
    }
}
