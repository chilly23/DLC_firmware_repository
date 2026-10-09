import QtQuick
import QtQuick.Controls

Item {
    onVisibleChanged:if(visible)diagnostics.refresh()
    Text {text:"Inspect the system or run a targeted check.";font.family:theme.fontFamily;font.pixelSize:23;color:theme.muted}
    Row {y:52;spacing:12
        LobbyButton {objectName:"diagnoseSystem";width:270;glyph:"diagnostics";text:diagnostics.busy?"Checking…":"Diagnose system";enabled:!diagnostics.busy;onClicked:diagnostics.run()}
        LobbyButton {objectName:"screenCheck";width:244;glyph:"screencheck";text:"Screen check";onClicked:diagnostics.screenCheck()}
        LobbyButton {objectName:"retryGpio";width:225;glyph:"retry";text:"Retry GPIO";onClicked:diagnostics.retryGpio()}
        LobbyButton {objectName:"retryDisplay";width:235;glyph:"retry";text:"Retry display";onClicked:diagnostics.retryDisplay()}
        LobbyButton {width:240;glyph:"knob";text:"Input calibration";onClicked:workspace.openSettings("control","")}
        LobbyButton {objectName:"diagnosticsExport";width:230;glyph:"logs";text:"Export report";enabled:diagnostics.rows.length>0;onClicked:diagnostics.export()}
    }
    Text {y:128;width:1504;text:diagnostics.summary;font.family:theme.fontFamily;font.pixelSize:20;color:theme.foreground;elide:Text.ElideRight}
    ListView {y:174;width:1504;height:344;clip:true;model:diagnostics.rows;spacing:6
        ScrollBar.vertical:ScrollBar{}
        delegate:Rectangle {
            required property var modelData
            width:1488;height:62;color:theme.light?"#D7DAD7":"#282828"
            Rectangle {x:16;y:24;width:14;height:14;radius:7;color:modelData.state==="Passed"?"#32D74B":modelData.state==="Failed"?"#FF453A":"#FF9F0A"}
            Text {x:48;y:18;width:295;text:modelData.name;font.family:theme.fontFamily;font.pixelSize:23;color:theme.foreground}
            Text {x:360;y:21;width:910;text:modelData.detail;font.family:theme.fontFamily;font.pixelSize:18;color:theme.muted;elide:Text.ElideRight}
            Text {x:1300;y:20;width:160;text:modelData.state;font.family:theme.fontFamily;font.pixelSize:20;color:theme.foreground;horizontalAlignment:Text.AlignRight}
        }
        Column {visible:diagnostics.rows.length===0;spacing:24;y:25
            Text {text:"GPIO · "+diagnostics.gpioStatus;width:1450;wrapMode:Text.WordWrap;color:theme.muted;font.family:theme.fontFamily;font.pixelSize:23}
            Text {text:"Display · "+diagnostics.displayStatus;width:1450;wrapMode:Text.WordWrap;color:theme.muted;font.family:theme.fontFamily;font.pixelSize:23}
            Text {text:"Screen check tests corner touches, tracing, dragging and display colours.";color:theme.muted;font.family:theme.fontFamily;font.pixelSize:22}
        }
    }
}
