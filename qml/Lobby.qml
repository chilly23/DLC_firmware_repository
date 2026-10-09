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
    signal emissionRequested(int index)
    readonly property var titles: ({lobby:"Lobby",buttons:"Buttons Panel",files:"File Manager",monitor:"System Monitoring",control:"Control Parameters",diagnostics:"Diagnostics",manual:"Digital Manual",dlc:"DLC View",graphs:"Graph Size",legal:"Legal Information",laser:"Laser Config",sub:"Sub Parameters",home:"Home Controls"})
    readonly property var tiles: [
        {key:"buttons",name:"Buttons Panel",icon:"buttons",col:0,row:0,cw:3,rh:2,detail:"Shortcuts & side-panel order"},
        {key:"control",name:"Control Parameters",icon:"control",col:3,row:0,cw:2,rh:3,detail:"CC / TC / PC\nSetpoints & readbacks"},
        {key:"graphs",name:"Graph Size",icon:"graphsize",col:5,row:0,cw:3,rh:1,detail:"Small / Medium / Large"},
        {key:"screenshot",name:"Screenshot",icon:"camera",col:5,row:1,cw:1,rh:2},
        {key:"files",name:"File Manager",icon:"folder",col:6,row:1,cw:2,rh:2,detail:"Files, captures & exports"},
        {key:"diagnostics",name:"Diagnostics",icon:"diagnostics",col:0,row:2,cw:2,rh:1},
        {key:"monitor",name:"System Monitoring",icon:"monitor",col:2,row:2,cw:1,rh:2},
        {key:"laser",name:"Laser Config",icon:"emission",col:0,row:3,cw:2,rh:2,detail:"Limits & operating values"},
        {key:"dlc",name:"DLC View",icon:"cube",col:3,row:3,cw:2,rh:1,detail:"Coming later"},
        {key:"sub",name:"Sub Parameters",icon:"sliders",col:5,row:3,cw:1,rh:2},
        {key:"home",name:"Home Controls",icon:"home",col:6,row:3,cw:2,rh:1},
        {key:"legal",name:"Legal Info",icon:"legal",col:0,row:5,cw:1,rh:1},
        {key:"manual",name:"Digital Manual",icon:"book",col:1,row:5,cw:2,rh:1},
        {key:"display",name:"Display Settings",icon:"display",col:3,row:4,cw:2,rh:1},
        {key:"notifications",name:"Notifications",icon:"notifications",col:6,row:4,cw:1,rh:2},
        {key:"logs",name:"Logs",icon:"logs",col:7,row:4,cw:1,rh:2},
        {key:"about",name:"About",icon:"info",col:3,row:5,cw:1,rh:1},
        {key:"system",name:"System",icon:"control",col:2,row:4,cw:1,rh:1},
        {key:"function",name:"Signals",icon:"sliders",col:4,row:5,cw:1,rh:1},
        {key:"help",name:"Help",icon:"info",col:5,row:5,cw:1,rh:1}
    ]
    function open(target){page=target||"lobby";visible=true;forceActiveFocus();if(page==="files")workspace.refreshFiles()}
    function back(){if(page==="files" && filesPage.back())return;if(page==="sub" && subPage.path){subPage.back();return}if(page==="lobby")closed();else page="lobby"}
    function activate(key){
        if(key==="screenshot"){workspace.captureScreen();return}
        if(key==="logs"){logsRequested();return}
        let sections={display:"display",notifications:"notifications",about:"about",system:"system",function:"function",help:"help"}
        if(sections[key]){workspace.openSettings(sections[key],"");return}
        page=key
        if(key==="files")workspace.refreshFiles()
    }
    function updateObservers(){workspace.monitorSystem(visible && page==="monitor");parameters.observe(visible && ["control","laser","sub","home"].indexOf(page)>=0)}
    onPageChanged:{workspace.closePreview();updateObservers()}
    onVisibleChanged:updateObservers()
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
        FileManager {id:filesPage;anchors.fill:parent;visible:lobby.page==="files"}
        SystemMonitor {anchors.fill:parent;visible:lobby.page==="monitor"}
        ControlParameters {anchors.fill:parent;visible:lobby.page==="control";onEditRequested:function(i,key){lobby.editParameter(i,key)} onEmissionRequested:function(i){lobby.emissionRequested(i)}}
        LaserConfig {anchors.fill:parent;visible:lobby.page==="laser";onEditRequested:function(i,key){lobby.editParameter(i,key)}}
        SubParameters {id:subPage;anchors.fill:parent;visible:lobby.page==="sub";onEditRequested:function(i,key){lobby.editParameter(i,key)} onEmissionRequested:function(i){lobby.emissionRequested(i)}}
        HomeControls {anchors.fill:parent;visible:lobby.page==="home";onEditRequested:function(i,key){lobby.editParameter(i,key)}}
        DiagnosticsPage {anchors.fill:parent;visible:lobby.page==="diagnostics"}
        PlannedPage {anchors.fill:parent;visible:lobby.page==="dlc";title:"DLC View";glyph:"cube";detail:"This space is reserved for DLC functionality. No features are enabled here yet."}
        PlannedPage {anchors.fill:parent;visible:lobby.page==="legal";title:"Legal Information";glyph:"legal";detail:"Product legal information will be added here when the approved content is supplied."}
        PlannedPage {anchors.fill:parent;visible:lobby.page==="manual";title:"Digital Manual";glyph:"book";detail:"The product manual will be added here in a future release."}
    }

    Text {x:48;y:684;width:1300;text:workspace.message;elide:Text.ElideMiddle;color:theme.muted;font.family:theme.fontFamily;font.pixelSize:16}
    LobbyButton {visible:page==="buttons";x:1310;y:670;width:244;height:42;text:"Reset button order";onClicked:workspace.resetButtons()}
}
