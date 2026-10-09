import QtQuick
import QtQuick.Controls

Item {
    id: root
    property int revision: 0
    Connections { target: workspace; function onChanged(){root.revision++} }
    Text { x:0;y:0;text:"Choose each shortcut, then drag the rows to reorder the Home side panels.";font.family:theme.fontFamily;font.pixelSize:21;color:theme.muted }
    Row {
        y:50;spacing:24
        Repeater {
            model:2
            delegate: Rectangle {
                id: panel
                required property int index
                property var order: {root.revision;return workspace.panelOrder(index)}
                width:740;height:454;radius:0;color:theme.light?"#E0E2E0":"#222222"
                Text {x:22;y:18;text:index===0?"Left button panel":"Right button panel";font.family:theme.fontFamily;font.pixelSize:26;color:theme.foreground}
                ComboBox {
                    id: shortcut;objectName:"shortcutAssignment"+panel.index
                    property string navLabel:(panel.index===0?"Left":"Right")+" shortcut action"
                    property string navKind:"choice"
                    function stepFromKnob(amount){let index=(currentIndex+amount%count+count)%count;workspace.setShortcut(panel.index,workspace.shortcutActions[index].key)}
                    x:300;y:13;width:417;height:52
                    model:workspace.shortcutActions;textRole:"name";valueRole:"key"
                    currentIndex:{root.revision;let value=workspace.shortcut(panel.index);return workspace.shortcutActions.findIndex(a=>a.key===value)}
                    onActivated:workspace.setShortcut(panel.index,currentValue)
                    font.family:theme.fontFamily;font.pixelSize:18
                    palette.button: "#363636";palette.buttonText:"#F0F1EE";palette.text:"#F0F1EE";palette.base:"#303030";palette.highlight:"#555555"
                    palette.window:theme.light?"#E2E4E2":"#303030";palette.windowText:theme.foreground
                    Accessible.name:(panel.index===0?"Left":"Right")+" shortcut action"
                }
                Item {
                    id: rows;x:20;y:82;width:700;height:355
                    Repeater {
                        model:panel.order
                        delegate: Item {
                            id: row
                            required property string modelData
                            required property int index
                            x:0;y:index*70;width:700;height:62
                            Rectangle {
                                id: card;objectName:"buttonOrder_"+panel.index+"_"+row.modelData
                                width:row.width;height:row.height;radius:0;color:handle.pressed?"#535353":theme.light?"#CED1CE":"#303030"
                                z:handle.pressed?2:0
                                Icon {x:18;y:17;width:28;height:28;kind:row.modelData;ink:theme.foreground}
                                Text {x:64;anchors.verticalCenter:parent.verticalCenter;text:row.modelData.charAt(0).toUpperCase()+row.modelData.slice(1);color:theme.foreground;font.family:theme.fontFamily;font.pixelSize:22}
                                Icon {x:416;y:21;width:20;height:20;kind:"reorder";ink:theme.muted}
                                Text {x:445;anchors.verticalCenter:parent.verticalCenter;text:"Drag";color:theme.muted;font.family:theme.fontFamily;font.pixelSize:19}
                                MouseArea {
                                    id:handle;objectName:"reorderHandle_"+panel.index+"_"+row.modelData
                                    x:0;y:0;width:538;height:parent.height
                                    drag.target:card;drag.axis:Drag.YAxis;drag.minimumY:-row.y;drag.maximumY:280-row.y
                                    preventStealing:true
                                    onPressed:row.z=5
                                    onReleased:{let target=Math.max(0,Math.min(4,Math.round((row.y+card.y)/70)));card.y=0;row.z=0;workspace.moveButton(panel.index,row.index,target)}
                                    onCanceled:{card.y=0;row.z=0}
                                }
                                LobbyButton {objectName:"orderUp_"+panel.index+"_"+row.modelData;x:550;y:7;width:60;height:48;glyph:"up";enabled:row.index>0;navLabel:"Move "+row.modelData+" up";onClicked:workspace.moveButton(panel.index,row.index,row.index-1)}
                                LobbyButton {objectName:"orderDown_"+panel.index+"_"+row.modelData;x:622;y:7;width:60;height:48;glyph:"down";enabled:row.index<4;navLabel:"Move "+row.modelData+" down";onClicked:workspace.moveButton(panel.index,row.index,row.index+1)}
                            }
                        }
                    }
                }
            }
        }
    }
}
