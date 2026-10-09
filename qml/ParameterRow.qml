import QtQuick

Rectangle {
    id: row
    required property var entry
    property int channelIndex: 0
    property bool selected: false
    property string navLabel: entry.kind === "read" ? "" : entry.label
    signal editRequested(int channelIndex, string key)
    signal branchRequested(string path)
    signal emissionRequested(int channelIndex)
    height: 52
    color: selected ? theme.active : theme.light ? "#D7DAD7" : "#272727"
    property color ink: selected ? theme.activeInk : theme.foreground
    Text { x:16; y:entry.caption ? 4 : 13; width:parent.width-245; text:entry.label; elide:Text.ElideRight; font.family:theme.fontFamily; font.pixelSize:20; color:row.ink }
    Text { x:16; y:29; width:parent.width-170; visible:!!entry.caption; text:entry.caption; elide:Text.ElideRight; font.family:theme.fontFamily; font.pixelSize:15; color:selected?theme.activeInk:theme.muted }
    Text { x:parent.width-248; y:8; width:entry.kind==="read"?204:224; height:32; visible:entry.kind!=="toggle" && entry.kind!=="branch"; text:entry.value+(entry.unit?" "+entry.unit:""); horizontalAlignment:Text.AlignRight; elide:Text.ElideRight; font.family:theme.fontFamily; font.pixelSize:21; color:row.ink }
    Icon { x:parent.width-33; y:17; width:18; height:18; visible:entry.kind==="read"; kind:"lock"; ink:theme.muted }
    Icon { x:parent.width-44; y:13; width:26; height:26; visible:entry.kind==="branch"; kind:"chevronRight"; ink:row.ink }
    Rectangle {
        x:parent.width-91; y:9; width:72; height:34; radius:17; visible:entry.kind==="toggle"
        color:entry.on?theme.active:theme.light?"#A6AAA6":"#474747"
        Rectangle { x:entry.on?41:5; y:5; width:24; height:24; radius:12; color:entry.on?theme.activeInk:theme.foreground; Behavior on x {NumberAnimation{duration:120}} }
    }
    Rectangle { anchors.bottom:parent.bottom; width:parent.width; height:1; color:theme.light?"#BCC0BC":"#3A3A3A" }
    MouseArea {
        anchors.fill:parent; enabled:entry.kind!=="read"
        onClicked: {
            if(entry.kind==="number")row.editRequested(row.channelIndex,entry.key)
            else if(entry.kind==="toggle") {
                if(entry.key==="cc_enabled")row.emissionRequested(row.channelIndex)
                else parameters.toggleControl(row.channelIndex,entry.key)
            } else row.branchRequested(entry.path)
        }
    }
    Accessible.role:entry.kind==="toggle"?Accessible.CheckBox:entry.kind==="read"?Accessible.StaticText:Accessible.Button
    Accessible.name:entry.label+" "+entry.value
}
