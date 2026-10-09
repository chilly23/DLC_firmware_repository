import QtQuick
import QtQuick.Controls

Item {
    id: root
    property string path:""
    property string selected:"laser1"
    property int revision:0
    signal editRequested(int index,string key)
    signal emissionRequested(int index)
    function indexFor(value){return value.indexOf("laser2")===0?1:0}
    function back(){let parts=path.split("/");parts.pop();selected=path;path=parts.join("/")}
    Connections {target:parameters;function onChanged(){root.revision++}}
    LobbyButton {objectName:"parameterUp";width:180;height:44;text:"Up one level";glyph:"chevronLeft";enabled:root.path!=="";onClicked:root.back()}
    Text {x:202;y:8;width:1270;text:"Parameters"+(root.path?" / "+root.path.replace(/\//g," / "):"");font.family:theme.fontFamily;font.pixelSize:24;color:theme.foreground;elide:Text.ElideMiddle}
    Row {y:62;spacing:24
        Repeater {model:2
            Rectangle {
                id: pane;required property int index
                property string branch:index===0?root.path:root.selected
                width:740;height:451;color:theme.light?"#D7DAD7":"#272727"
                Text {x:16;y:12;text:pane.index===0?(root.path||"System parameters"):(root.selected||"Select a parameter group");font.family:theme.fontFamily;font.pixelSize:24;color:theme.foreground}
                LobbyButton {objectName:"parameterEnter";visible:pane.index===1 && root.selected!=="";x:545;y:5;width:178;height:42;text:"Open group";glyph:"chevronRight";onClicked:{root.path=root.selected;root.selected=""}}
                ListView {y:60;width:740;height:386;clip:true;boundsBehavior:Flickable.StopAtBounds
                    model:{root.revision;return pane.index===1&&!root.selected?0:parameters.treeRows(pane.branch).length}
                    ScrollBar.vertical:ScrollBar{}
                    delegate:ParameterRow {
                        required property int index
                        property var modelData:{root.revision;return parameters.treeRows(pane.branch)[index] || parameters.treeRows("")[0]}
                        objectName:"sub_"+pane.index+"_"+modelData.key
                        width:740;height:55;entry:modelData;channelIndex:root.indexFor(pane.branch)
                        selected:modelData.kind==="branch" && modelData.path===root.selected
                        onBranchRequested:function(next){if(pane.index===0)root.selected=next;else{root.path=pane.branch;root.selected=next}}
                        onEditRequested:function(i,key){root.editRequested(i,key)}
                        onEmissionRequested:function(i){root.emissionRequested(i)}
                    }
                }
            }
        }
    }
}
