import QtQuick
import QtQuick.Controls

Rectangle {
    id: lobby
    objectName:"lobby"
    color:theme.background
    property string page:"lobby"
    property int revision:0
    signal closed()
    signal logsRequested()
    signal editParameter(int index,string key)
    signal chooseHomeField(int side,bool bottom)
    readonly property var titles: ({lobby:"Lobby",buttons:"Buttons Panel",files:"File Manager",monitor:"System Monitoring",dlc:"DLC",graphs:"Graph Size",legal:"Legal Info",laser:"Laser Config",sub:"Sub Parameters",home:"Home Controls"})
    readonly property var tiles: [
        {key:"buttons",name:"Buttons Panel",icon:"buttons",col:0,row:0,cw:3,rh:2,detail:"Shortcuts & side-panel order"},
        {key:"dlc",name:"DLC",icon:"cube",col:3,row:0,cw:2,rh:3,detail:"36380-L\nController & 3D assembly"},
        {key:"graphs",name:"Graph Size",icon:"graphsize",col:5,row:0,cw:3,rh:1,detail:"Small / Medium / Large"},
        {key:"screenshot",name:"Screenshot",icon:"camera",col:5,row:1,cw:1,rh:2},
        {key:"files",name:"File Manager",icon:"folder",col:6,row:1,cw:2,rh:2,detail:"Files, captures & exports"},
        {key:"diagnostics",name:"Diagnostics",icon:"diagnostics",col:0,row:2,cw:2,rh:1},
        {key:"monitor",name:"System Monitoring",icon:"monitor",col:2,row:2,cw:1,rh:2},
        {key:"control",name:"Control Parameters",icon:"control",col:0,row:3,cw:2,rh:2,detail:"Signal & control settings"},
        {key:"laser",name:"Laser Config",icon:"emission",col:3,row:3,cw:2,rh:1},
        {key:"sub",name:"Sub Parameters",icon:"sliders",col:5,row:3,cw:1,rh:2},
        {key:"home",name:"Home Controls",icon:"home",col:6,row:3,cw:2,rh:1},
        {key:"legal",name:"Legal Info",icon:"legal",col:0,row:5,cw:1,rh:1},
        {key:"manual",name:"Digital Manual",icon:"book",col:1,row:5,cw:2,rh:1},
        {key:"display",name:"Display Settings",icon:"display",col:3,row:4,cw:2,rh:1},
        {key:"notifications",name:"Notifications",icon:"notifications",col:6,row:4,cw:1,rh:2},
        {key:"logs",name:"Logs",icon:"logs",col:7,row:4,cw:1,rh:2},
        {key:"about",name:"About",icon:"info",col:3,row:5,cw:1,rh:1},
        {key:"reserved1",name:"Placeholder",icon:"placeholder",col:2,row:4,cw:1,rh:1,placeholder:true},
        {key:"reserved2",name:"Placeholder",icon:"placeholder",col:4,row:5,cw:1,rh:1,placeholder:true},
        {key:"reserved3",name:"Placeholder",icon:"placeholder",col:5,row:5,cw:1,rh:1,placeholder:true}
    ]
    function open(target){page=target||"lobby";visible=true;forceActiveFocus();if(page==="files")workspace.refreshFiles()}
    function back(){if(page==="lobby")closed();else page="lobby"}
    function activate(key){
        if(key==="screenshot"){workspace.captureScreen();return}
        if(key==="logs"){logsRequested();return}
        let sections={diagnostics:"control",control:"function",manual:"help",display:"display",notifications:"notifications",about:"about"}
        if(sections[key]){workspace.openSettings(sections[key],"");return}
        page=key
        if(key==="files")workspace.refreshFiles()
    }
    onPageChanged:workspace.monitorSystem(visible && page==="monitor")
    onVisibleChanged:workspace.monitorSystem(visible && page==="monitor")
    Connections {target:ctl;function onChanged(){lobby.revision++}}
    MouseArea {anchors.fill:parent}
    Keys.onEscapePressed:back()
    LobbyButton {objectName:"lobbyBack";x:36;y:30;width:152;height:60;text:page==="lobby"?"Home":"Lobby";glyph:"chevronLeft";onClicked:lobby.back()}
    Text {x:218;y:23;text:lobby.titles[lobby.page]||"Lobby";font.family:theme.fontFamily;font.pixelSize:40;color:theme.foreground}
    Text {x:220;y:76;text:page==="lobby"?"Tools, configuration and information":"Lobby / "+(lobby.titles[lobby.page]||"");font.family:theme.fontFamily;font.pixelSize:18;color:theme.muted}
    LobbyButton {objectName:"lobbyHome";x:1410;y:30;width:154;height:60;text:"Home";glyph:"home";onClicked:lobby.closed()}
    Rectangle {x:36;y:119;width:1528;height:1;color:theme.raised}
    Item {
        id:body;x:48;y:143;width:1504;height:522
        Item {
            visible:lobby.page==="lobby";anchors.fill:parent
            Repeater {
                model:lobby.tiles
                delegate: Rectangle {
                    required property var modelData
                    property string navLabel:modelData.placeholder?"":modelData.name
                    property bool horizontal:modelData.rh===1
                    property bool prominent:modelData.cw>=2 && modelData.rh>=2
                    property bool placeholder:modelData.placeholder===true
                    property color tileInk:placeholder?theme.muted:theme.foreground
                    objectName:"lobbyTile_"+modelData.key
                    x:modelData.col*189;y:modelData.row*(530/6)
                    width:modelData.cw*189-8;height:modelData.rh*(530/6)-8
                    radius:0;color:press.pressed?"#484848":theme.light?(placeholder?"#E1E3E1":"#D7DAD7"):(placeholder?"#1B1B1B":prominent?"#303030":"#272727")
                    border.width:placeholder?1:0;border.color:theme.light?"#B5BAB5":"#373737"
                    Icon {x:horizontal?16:22;y:horizontal?(parent.height-height)/2:22;width:horizontal?30:prominent?48:37;height:width;kind:modelData.icon;ink:parent.tileInk}
                    Text {x:parent.horizontal?58:22;y:parent.horizontal?(modelData.detail?15:(parent.height-height)/2):parent.prominent?87:76;width:parent.width-x-16;text:modelData.name;font.family:theme.fontFamily;font.pixelSize:parent.horizontal?(modelData.cw===1?17:21):parent.prominent?28:20;color:parent.tileInk;wrapMode:Text.WordWrap}
                    Text {visible:!!modelData.detail;x:parent.horizontal?58:22;y:parent.horizontal?46:130;width:parent.width-x-16;text:modelData.detail||"";font.family:theme.fontFamily;font.pixelSize:17;color:theme.muted;wrapMode:Text.WordWrap}
                    MouseArea {id:press;anchors.fill:parent;enabled:!parent.placeholder;onClicked:lobby.activate(modelData.key)}
                    Accessible.role:Accessible.Button;Accessible.name:modelData.name
                }
            }
        }
        ButtonsPanel {objectName:"buttonsPanel";anchors.fill:parent;visible:lobby.page==="buttons"}
        Item {
            anchors.fill:parent;visible:lobby.page==="graphs"
            Text {text:"Choose how much space the Home graphs occupy.";color:theme.muted;font.family:theme.fontFamily;font.pixelSize:24}
            Row {y:75;spacing:24
                Repeater {model:["Small","Medium","Large"]
                    Rectangle {
                        id:graphCard
                        required property string modelData
                        objectName:"graphSize_"+modelData
                        property string navLabel:modelData+" graphs"
                        width:485;height:315;radius:0;color:workspace.graphSize===modelData?"#D9D9D9":theme.light?"#D7DAD7":"#282828"
                        property color ink:workspace.graphSize===modelData?"#111111":theme.foreground
                        Icon {x:32;y:32;width:55;height:55;kind:"graphsize";ink:parent.ink}
                        Text {x:32;y:108;text:modelData;font.family:theme.fontFamily;font.pixelSize:34;color:parent.ink}
                        Row {x:32;y:188;spacing:8
                            Repeater {model:2;Rectangle {width:graphCard.modelData==="Small"?124:graphCard.modelData==="Medium"?160:198;height:58;color:"transparent";border.width:2;border.color:parent.parent.ink;radius:0}}
                        }
                        MouseArea {anchors.fill:parent;onClicked:workspace.setGraphSize(modelData)}
                    }
                }
            }
            Text {y:430;text:"Applied immediately to both Home graphs. Your view ranges and signal settings stay intact.";color:theme.muted;font.family:theme.fontFamily;font.pixelSize:21}
        }
        Item {
            anchors.fill:parent;visible:lobby.page==="files"
            Row {spacing:12
                LobbyButton {text:"Up";width:96;onClicked:workspace.parentFolder()}
                LobbyButton {text:"Data";width:140;onClicked:workspace.browse("data")}
                LobbyButton {text:"Screenshots";width:180;onClicked:workspace.browse("screenshots")}
                LobbyButton {text:"Exports";width:140;onClicked:workspace.browse("exports")}
                LobbyButton {text:"User files";width:160;onClicked:workspace.browse("home")}
                LobbyButton {text:"Refresh";width:140;onClicked:workspace.refreshFiles()}
            }
            Text {y:72;width:parent.width;text:workspace.folder;color:theme.muted;font.family:theme.fontFamily;font.pixelSize:18;elide:Text.ElideMiddle}
            ListView {objectName:"fileList";y:112;width:parent.width;height:402;clip:true;model:workspace.files;spacing:8
                ScrollBar.vertical:ScrollBar {}
                delegate:Rectangle {
                    required property var modelData
                    width:ListView.view.width-16;height:65;radius:0;color:theme.light?"#D7DAD7":"#282828"
                    property string navLabel:modelData.name
                    Icon {x:18;y:17;width:30;height:30;kind:modelData.directory?"folder":"logs";ink:theme.foreground}
                    Text {x:66;y:18;width:900;text:modelData.name;font.family:theme.fontFamily;font.pixelSize:22;color:theme.foreground;elide:Text.ElideMiddle}
                    Text {x:1000;y:20;width:145;text:modelData.size;font.family:theme.fontFamily;font.pixelSize:18;color:theme.muted}
                    Text {x:1180;y:20;text:modelData.modified;font.family:theme.fontFamily;font.pixelSize:18;color:theme.muted}
                    MouseArea {anchors.fill:parent;onClicked:workspace.openFile(modelData.path)}
                }
                Text {anchors.centerIn:parent;visible:workspace.files.length===0;text:"This folder is empty";color:theme.muted;font.family:theme.fontFamily;font.pixelSize:24}
            }
        }
        Item {
            anchors.fill:parent;visible:lobby.page==="monitor"
            Text {text:"Live host readings · updated every second";color:theme.muted;font.family:theme.fontFamily;font.pixelSize:22}
            Grid {y:58;columns:4;spacing:16
                Repeater {model:workspace.metrics
                    Rectangle {required property var modelData;width:364;height:202;radius:0;color:theme.light?"#D7DAD7":"#282828"
                        Text {x:24;y:25;width:316;text:modelData.name;font.family:theme.fontFamily;font.pixelSize:20;color:theme.muted}
                        Text {x:24;y:70;width:316;height:105;text:modelData.value;font.family:theme.fontFamily;font.pixelSize:28;color:theme.foreground;wrapMode:Text.WordWrap;elide:Text.ElideRight}
                    }
                }
            }
        }
        Item {
            anchors.fill:parent;visible:lobby.page==="laser"||lobby.page==="sub"
            Text {text:lobby.page==="laser"?"Laser operating values":"Additional control values";color:theme.muted;font.family:theme.fontFamily;font.pixelSize:22}
            Row {y:53;spacing:24
                Repeater {model:2
                    Column {id:laserColumn;required property int index;spacing:10;width:740
                        Text {text:"Laser "+(index+1);font.family:theme.fontFamily;font.pixelSize:28;color:theme.foreground}
                        Repeater {model:lobby.page==="laser"?["current","temperature","umax"]:["pid","feedforward","offset","amplitude","frequency","setpoint"]
                            Rectangle {required property string modelData;width:740;height:64;radius:0;color:theme.light?"#D7DAD7":"#282828"
                                property var spec:ctl.parameter(modelData)
                                property string navLabel:"Laser "+(laserColumn.index+1)+" "+spec.label
                                Text {x:20;anchors.verticalCenter:parent.verticalCenter;text:parent.spec.label;font.family:theme.fontFamily;font.pixelSize:22;color:theme.foreground}
                                Text {x:400;width:318;anchors.verticalCenter:parent.verticalCenter;text:{lobby.revision;return ctl.value(laserColumn.index,modelData)+" "+parent.spec.unit}
                                    font.family:theme.fontFamily;font.pixelSize:25;color:theme.foreground;horizontalAlignment:Text.AlignRight}
                                MouseArea {anchors.fill:parent;onClicked:lobby.editParameter(laserColumn.index,modelData)}
                            }
                        }
                    }
                }
            }
        }
        Item {
            anchors.fill:parent;visible:lobby.page==="home"
            Text {text:"Choose the value shown in each Home corner.";color:theme.muted;font.family:theme.fontFamily;font.pixelSize:24}
            Grid {y:65;columns:2;spacing:24
                Repeater {model:4
                    Rectangle {required property int index;width:740;height:176;radius:0;color:theme.light?"#D7DAD7":"#282828"
                        property int side:index%2
                        property bool lowerCorner:index>=2
                        property var channel:{lobby.revision;return ctl.channel(side===0?ctl.leftChannel:ctl.rightChannel)}
                        property string field:lowerCorner?channel.bottom:channel.top
                        property string navLabel:(side===0?"Left":"Right")+(lowerCorner?" bottom":" top")+" corner"
                        Text {x:28;y:24;text:parent.navLabel;font.family:theme.fontFamily;font.pixelSize:23;color:theme.muted}
                        Text {x:28;y:70;text:ctl.parameter(parent.field).label;font.family:theme.fontFamily;font.pixelSize:31;color:theme.foreground}
                        MouseArea {anchors.fill:parent;onClicked:lobby.chooseHomeField(parent.side,parent.lowerCorner)}
                    }
                }
            }
            LobbyButton {y:475;width:360;text:theme.buttonLabels?"Side buttons: icons + names":"Side buttons: icons only";onClicked:workspace.toggleButtonLabels()}
        }
        Rectangle {
            visible:lobby.page==="dlc";anchors.fill:parent;radius:0;color:theme.light?"#D7DAD7":"#282828"
            Icon {x:48;y:50;width:105;height:105;kind:"cube";ink:theme.foreground}
            Text {x:200;y:48;text:"36380-L";font.family:theme.fontFamily;font.pixelSize:52;color:theme.foreground}
            Text {x:200;y:118;text:"Digital Laser Controller";font.family:theme.fontFamily;font.pixelSize:28;color:theme.muted}
            Text {x:48;y:214;width:1380;text:"DLC controls and the interactive 3D assembly are available here. The assembly viewer uses its own GPU rendering window.";font.family:theme.fontFamily;font.pixelSize:24;color:theme.foreground;wrapMode:Text.WordWrap}
            LobbyButton {x:48;y:338;width:340;height:68;text:"Open 3D assembly";glyph:"cube";onClicked:workspace.openDlcModel()}
            LobbyButton {x:408;y:338;width:280;height:68;text:"Laser configuration";onClicked:lobby.page="laser"}
            LobbyButton {x:708;y:338;width:280;height:68;text:"Controller information";onClicked:workspace.openSettings("about","")}
        }
        Rectangle {
            visible:lobby.page==="legal";anchors.fill:parent;radius:0;color:theme.light?"#D7DAD7":"#282828"
            Text {x:32;y:30;text:"Software notices";font.family:theme.fontFamily;font.pixelSize:31;color:theme.foreground}
            Text {x:32;y:98;width:1420;text:"Nexatom application v1.15\n\nThis application uses Python, Qt and PySide6. Third-party license terms and copyright notices remain with their respective packages.\n\nApplication-specific legal terms have not been supplied. Add your approved product license, warranty and regulatory documents to this page before product release.\n\nThe laser traces in this build remain simulated. The existing host and GPIO integrations are unchanged.";font.family:theme.fontFamily;font.pixelSize:24;color:theme.foreground;wrapMode:Text.WordWrap}
        }
    }
    Text {x:48;y:684;width:1300;text:workspace.message;elide:Text.ElideMiddle;color:theme.muted;font.family:theme.fontFamily;font.pixelSize:16}
    LobbyButton {visible:page==="buttons";x:1310;y:670;width:244;height:42;text:"Reset button order";onClicked:workspace.resetButtons()}
}
