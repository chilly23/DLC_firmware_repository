import QtQuick

Item {
    id: root
    property int revision:0
    signal editRequested(int index,string key)
    Connections {target:parameters;function onChanged(){root.revision++}}
    Text {text:"Operating limits and setpoints · shared with Home controls";font.family:theme.fontFamily;font.pixelSize:22;color:theme.muted}
    Row {y:56;spacing:24
        Repeater {model:2
            Rectangle {
                id: column;required property int index
                width:740;height:424;color:theme.light?"#D7DAD7":"#272727"
                Text {x:20;y:16;text:"Laser "+(column.index+1)+" Config";font.family:theme.fontFamily;font.pixelSize:29;color:theme.foreground}
                Column {y:68;width:740
                    Repeater {model:5
                        ParameterRow {required property int index;property var modelData:{root.revision;return parameters.laserRows(column.index)[index]} objectName:"laserConfig_"+column.index+"_"+modelData.key;width:740;height:68;entry:modelData;channelIndex:column.index;onEditRequested:function(i,key){root.editRequested(i,key)}}
                    }
                }
            }
        }
    }
    Text {y:494;text:"Lock icons identify read-only values. Limits are validated before a setpoint changes.";font.family:theme.fontFamily;font.pixelSize:18;color:theme.muted}
}
