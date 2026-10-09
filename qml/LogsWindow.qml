import QtQuick
import QtQuick.Window
import QtQuick.Controls

Window {
    id: logs
    objectName:"logsWindow"
    property var homeWindow
    property bool confirmClear:false
    width:1600;height:720;minimumWidth:800;minimumHeight:360
    visible:false;color:theme.background;title:"NEXATOM · Logs"
    flags:Qt.Window|Qt.FramelessWindowHint
    transientParent:homeWindow
    function open(){confirmClear=false;screen=homeWindow.screen;showFullScreen();requestActivate();surface.forceActiveFocus()}
    function dismiss(){confirmClear=false;hide();homeWindow.requestActivate()}
    onClosing:function(close){close.accepted=false;dismiss()}
    onVisibleChanged:workspace.activateLogs(visible)
    Item {
        id:surface;objectName:"logsSurface"
        width:1600;height:720;scale:Math.min(logs.width/1600,logs.height/720);transformOrigin:Item.TopLeft
        x:(logs.width-width*scale)/2;y:(logs.height-height*scale)/2
        Keys.onEscapePressed:logs.confirmClear?logs.confirmClear=false:logs.dismiss()
        Text {x:40;y:24;text:"User logs";color:theme.foreground;font.family:theme.fontFamily;font.pixelSize:36}
        Text {x:42;y:76;text:workspace.logRows.length+" records";color:theme.muted;font.family:theme.fontFamily;font.pixelSize:20}
        Row {x:700;y:26;spacing:14
            LobbyButton {objectName:"logsLive";text:workspace.logLive?"Live":"Paused";width:140;emphasized:workspace.logLive;onClicked:workspace.toggleLogLive()}
            LobbyButton {objectName:"logsExport";text:"Export";width:140;onClicked:workspace.exportLogs()}
            LobbyButton {objectName:"logsClear";text:"Clear logs";width:174;onClicked:logs.confirmClear=true}
            ComboBox {
                objectName:"logsLevel";width:190;height:56;model:["All","Default","Warning","Critical"]
                currentIndex:["all","default","warning","critical"].indexOf(workspace.logLevel)
                onActivated:workspace.setLogLevel(currentText.toLowerCase())
                font.family:theme.fontFamily;font.pixelSize:21
                palette.button:"#303030";palette.buttonText:"#F0F1EE";palette.text:"#F0F1EE";palette.base:"#303030"
                palette.window:theme.light?"#E2E4E2":"#303030";palette.windowText:theme.foreground
                property string navLabel:"Log level"
                property string navKind:"choice"
                function stepFromKnob(amount){workspace.setLogLevel(["all","default","warning","critical"][(currentIndex+amount%4+4)%4])}
            }
            LobbyButton {objectName:"logsClose";text:"Close";width:140;onClicked:logs.dismiss()}
        }
        Rectangle {x:40;y:128;width:1520;height:1;color:theme.raised}
        ListView {
            id:list;objectName:"logList";x:40;y:148;width:1520;height:514;clip:true;spacing:10
            model:workspace.logRows
            property int anchorId:0
            property real anchorOffset:0
            property bool restorePending:false
            Connections {target:workspace
                function onLogsAboutToChange(){
                    let index=Math.max(0,Math.floor(list.contentY/106))
                    list.anchorId=list.contentY>0 && workspace.logRows[index]?workspace.logRows[index].id:0
                    list.anchorOffset=list.contentY-index*106;list.restorePending=true
                }
                function onLogsChanged(){if(list.restorePending)Qt.callLater(function(){
                    if(!list.restorePending)return
                    list.restorePending=false
                    let index=workspace.logRows.findIndex(row=>row.id===list.anchorId)
                    list.contentY=index>=0?Math.max(0,Math.min(Math.max(0,list.contentHeight-list.height),index*106+list.anchorOffset)):0
                })}
            }
            ScrollBar.vertical:ScrollBar {}
            delegate:Rectangle {
                required property var modelData
                width:1500;height:96;radius:8;color:theme.surface
                property color levelInk:theme.light?({"#FF453A":"#AD251C","#FF9F0A":"#8D4900","#32D74B":"#176534","#D9D9D9":theme.foreground}[modelData.color]):modelData.color
                Rectangle {x:0;y:14;width:5;height:68;radius:2;color:modelData.color}
                Rectangle {x:18;y:15;width:12;height:12;radius:6;color:modelData.color;border.width:theme.light?1:0;border.color:theme.muted}
                Text {x:42;y:9;width:520;text:modelData.timestamp.replace("T"," ").slice(0,23);font.family:theme.fontFamily;font.pixelSize:18;color:theme.muted}
                Text {x:1110;y:9;width:170;text:modelData.status;font.family:theme.fontFamily;font.pixelSize:18;color:parent.levelInk}
                Text {x:1310;y:9;width:170;text:modelData.level.charAt(0).toUpperCase()+modelData.level.slice(1);font.family:theme.fontFamily;font.pixelSize:18;color:parent.levelInk}
                Text {x:18;y:38;width:1458;height:49;text:modelData.description;wrapMode:Text.WordWrap;elide:Text.ElideRight;font.family:theme.fontFamily;font.pixelSize:21;color:theme.foreground}
            }
            Text {anchors.centerIn:parent;visible:workspace.logRows.length===0;text:"No records for this level";color:theme.muted;font.family:theme.fontFamily;font.pixelSize:24}
        }
        Text {x:40;y:682;width:1520;text:workspace.message;font.family:theme.fontFamily;font.pixelSize:16;color:theme.muted;elide:Text.ElideMiddle}
        Row {x:40;y:104;spacing:22
            Repeater {model:[{color:"#FF453A",name:"Failed / critical"},{color:"#FF9F0A",name:"Warning"},{color:"#32D74B",name:"Completed"},{color:"#D9D9D9",name:"Information"}]
                Row {required property var modelData;spacing:8
                    Rectangle {y:3;width:10;height:10;radius:5;color:modelData.color}
                    Text {text:modelData.name;color:theme.muted;font.family:theme.fontFamily;font.pixelSize:15}
                }
            }
        }
        Rectangle {
            objectName:"logsClearConfirmation";anchors.fill:parent;color:"#AA000000";visible:logs.confirmClear
            MouseArea {anchors.fill:parent}
            Rectangle {x:435;y:235;width:730;height:240;radius:16;color:theme.surface
                Text {x:30;y:28;width:670;text:"Clear all user logs?";color:theme.foreground;font.family:theme.fontFamily;font.pixelSize:30}
                Text {x:30;y:84;width:670;text:"Error reports are retained.";color:theme.muted;font.family:theme.fontFamily;font.pixelSize:22}
                LobbyButton {objectName:"logsCancelClear";x:30;y:157;width:315;text:"Cancel";onClicked:logs.confirmClear=false}
                LobbyButton {objectName:"logsConfirmClear";x:365;y:157;width:335;text:"Clear logs";onClicked:{workspace.clearLogs();logs.confirmClear=false}}
            }
        }
    }
    Rectangle {visible:navigation.focus.active;x:navigation.focus.x-3;y:navigation.focus.y-3;width:navigation.focus.width+6;height:navigation.focus.height+6;color:"transparent";border.width:3;border.color:theme.foreground;radius:8}
}
