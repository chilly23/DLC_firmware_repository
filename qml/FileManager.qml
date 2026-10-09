import QtQuick
import QtQuick.Controls

Item {
    id:root
    function back(){if(workspace.preview.path){workspace.closePreview();return true}return false}
    Row {spacing:8
        LobbyButton {objectName:"filesUp";text:"Up";glyph:"chevronLeft";width:112;onClicked:workspace.parentFolder()}
        Repeater {model:[{key:"screenshots",name:"Screenshots"},{key:"recordings",name:"Recordings"},{key:"logs",name:"Logs"},{key:"exports",name:"Exports"},{key:"data",name:"App files"},{key:"home",name:"User files"}]
            LobbyButton {required property var modelData;objectName:"files_"+modelData.key;text:modelData.name;width:160;onClicked:workspace.browse(modelData.key)}
        }
        LobbyButton {text:"Refresh";glyph:"retry";width:152;onClicked:workspace.refreshFiles()}
        LobbyChoice {width:208;height:56;model:["Newest","Name","Largest"];currentIndex:model.indexOf(workspace.fileSort);navLabel:"Sort files";onActivated:function(index){workspace.sortFiles(model[index])}}
    }
    Text {y:74;width:1300;text:workspace.folder;font.family:theme.fontFamily;font.pixelSize:18;color:theme.muted;elide:Text.ElideMiddle}
    Text {y:74;x:1320;width:180;text:workspace.files.length+" items";font.family:theme.fontFamily;font.pixelSize:18;color:theme.muted;horizontalAlignment:Text.AlignRight}
    ListView {
        objectName:"fileList";y:112;width:1504;height:402;clip:true;model:workspace.files;spacing:8;boundsBehavior:Flickable.StopAtBounds
        ScrollBar.vertical:ScrollBar{}
        delegate:Rectangle {
            required property var modelData
            width:1488;height:66;color:theme.light?"#D7DAD7":"#282828"
            property string navLabel:modelData.name
            Image {x:12;y:7;width:70;height:52;visible:modelData.kind==="image";source:visible?modelData.url:"";sourceSize.width:140;sourceSize.height:104;fillMode:Image.PreserveAspectFit;asynchronous:true}
            Icon {x:29;y:18;width:30;height:30;visible:modelData.kind!=="image";kind:modelData.directory?"folder":"logs";ink:theme.foreground}
            Text {x:100;y:19;width:900;text:modelData.name;font.family:theme.fontFamily;font.pixelSize:22;color:theme.foreground;elide:Text.ElideMiddle}
            Text {x:1020;y:21;width:175;text:modelData.size;font.family:theme.fontFamily;font.pixelSize:18;color:theme.muted}
            Text {x:1206;y:21;text:modelData.modified;font.family:theme.fontFamily;font.pixelSize:18;color:theme.muted}
            MouseArea {anchors.fill:parent;onClicked:workspace.openFile(modelData.path)}
        }
        Text {anchors.centerIn:parent;visible:workspace.files.length===0;text:"No saved files in this folder";font.family:theme.fontFamily;font.pixelSize:26;color:theme.muted}
    }
    Rectangle {
        objectName:"filePreview";anchors.fill:parent;visible:!!workspace.preview.path;color:theme.background
        MouseArea {anchors.fill:parent}
        Text {x:0;y:8;width:940;text:workspace.preview.name||"";font.family:theme.fontFamily;font.pixelSize:25;color:theme.foreground;elide:Text.ElideMiddle}
        LobbyButton {x:982;width:282;text:"Open externally";onClicked:workspace.openExternal(workspace.preview.path)}
        LobbyButton {objectName:"filePreviewClose";x:1278;width:226;text:"Back to files";onClicked:workspace.closePreview()}
        Rectangle {y:76;width:1504;height:438;color:theme.light?"#D7DAD7":"#242424"
            Image {anchors.fill:parent;anchors.margins:12;visible:workspace.preview.kind==="image";source:visible?workspace.preview.url:"";fillMode:Image.PreserveAspectFit;asynchronous:true;sourceSize.width:2200;sourceSize.height:1400}
            ScrollView {anchors.fill:parent;anchors.margins:18;visible:workspace.preview.kind==="text";clip:true
                TextArea {text:workspace.preview.text||"";readOnly:true;selectByMouse:true;wrapMode:TextEdit.WrapAnywhere;color:theme.foreground;font.family:theme.fontFamily;font.pixelSize:20;background:null}
            }
            Text {anchors.centerIn:parent;width:1000;visible:workspace.preview.kind==="external";text:"Preview is not available for this file type.\nUse Open externally to view it in an installed application.";font.family:theme.fontFamily;font.pixelSize:25;color:theme.muted;horizontalAlignment:Text.AlignHCenter;wrapMode:Text.WordWrap}
        }
    }
}
