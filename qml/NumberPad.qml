import QtQuick

Item {
    id: pad
    property int channelIndex: 0
    property string fieldKey: "current"
    property int side: 0
    property bool lower: false
    property alias draft: editor.text
    property alias cursor: editor.cursorPosition
    property bool replaceDraft: true
    property string errorMessage: ""
    property var spec: ctl.parameter(fieldKey)
    property real acceptedValue: 0
    signal closed()

    function open(index, key, paneSide, isBottom) {
        channelIndex=index; fieldKey=key; side=paneSide; lower=isBottom
        acceptedValue=ctl.value(index,key)
        draft=Number(acceptedValue).toFixed(spec.decimals)
        cursor=draft.length; replaceDraft=true; errorMessage=""; visible=true
        editor.forceActiveFocus()
    }
    function key(value) {
        errorMessage=""
        if(value === "clearAll") {draft="";cursor=0;replaceDraft=false;return}
        if(value === "enter") {
            errorMessage=ctl.setValue(channelIndex, fieldKey, draft)
            if(errorMessage === "") pad.closed()
            return
        }
        if(value === "close") { pad.closed(); return }
        if(value === "left" || value === "right") {
            replaceDraft=false; cursor=Math.max(0,Math.min(draft.length,cursor+(value==="left"?-1:1))); return
        }
        if(value === "backspace") {
            if(replaceDraft) { draft="";cursor=0;replaceDraft=false }
            else if(cursor>0) { let p=cursor;draft=draft.slice(0,p-1)+draft.slice(p);cursor=p-1 }
            return
        }
        if(value === "-") {
            replaceDraft=false
            let p=cursor
            if(draft.startsWith("-")) {draft=draft.slice(1);cursor=Math.max(0,p-1)}
            else {draft="-"+draft;cursor=p+1}
            return
        }
        if(replaceDraft) {draft="";cursor=0;replaceDraft=false}
        if(draft.length>=14 || (value === "." && draft.indexOf(".")>=0)) return
        let p=cursor;draft=draft.slice(0,p)+value+draft.slice(p);cursor=p+1
    }

    Rectangle { anchors.fill: parent; color: "#000000"; opacity: .76 }
    MouseArea { anchors.fill: parent; onClicked: pad.closed() }
    ParameterTile {
        x: pad.side===0 ? 7 : 1175; y: pad.lower ? 634 : 7
        mirrored: pad.side===1; lower: pad.lower; editing: true
        fieldKey: pad.fieldKey; value: pad.acceptedValue
    }
    Rectangle {
        id: panel; objectName: "keypadPanel"; x: pad.side===0 ? 0 : 964; y: 111; width: 636; height: 507; color: theme.light ? theme.surface : "#252825"
        MouseArea { anchors.fill: parent } // Modal surface consumes taps between keys.
        Rectangle {
            x: 5; y: 5; width: 625; height: 70; color: theme.background
            TextInput { font.family:theme.fontFamily;
                id: editor; objectName: "keypadDraft"; x: 12; y: 7; width: 530; height: 40
                color: theme.foreground; font.pixelSize: theme.fontSize(34); clip: true; selectByMouse: true
                cursorVisible: pad.visible; maximumLength: 18; inputMethodHints: Qt.ImhFormattedNumbersOnly
                onTextEdited: pad.replaceDraft=false
                Keys.onReturnPressed: pad.key("enter")
                Keys.onEnterPressed: pad.key("enter")
                Keys.onEscapePressed: pad.closed()
            }
            Rectangle { x: 13; y: 46; width: 530; height: 1; color: "#A5AAA3" }
            Text { font.family:theme.fontFamily; x: 550; y: 9; text: pad.cursor + "/" + pad.draft.length; font.pixelSize: theme.fontSize(32); color: theme.foreground }
            Text { font.family:theme.fontFamily; x: 13; y: 49; text: pad.errorMessage; color: "#FF9991"; font.pixelSize: theme.fontSize(16) }
        }
        Repeater {
            model: ["7","8","9","4","5","6","1","2","3"]
            TouchButton {
                required property string modelData
                required property int index
                objectName: "key" + modelData
                x: 5+(index%3)*158; y: 84+Math.floor(index/3)*85; width: 148; height: 76; radius: 5
                normalColor:theme.background; text: modelData; textSize: 32
                onClicked: pad.key(modelData)
            }
        }
        TouchButton { objectName: "keyBackspace"; x: 482; y: 84; width: 148; height: 76; radius: 4; normalColor: theme.light ? theme.raised : "#3D403D"; iconName: "backspace";holdEnabled:true;onHeld:pad.key("clearAll");onClicked: pad.key("backspace") }
        TouchButton { objectName: "keyEnter"; x: 482; y: 169; width: 148; height: 246; radius: 4; normalColor: theme.light ? theme.raised : "#3D403D"; iconName: "enter"; onClicked: pad.key("enter") }
        TouchButton { objectName: "key0"; x: 5; y: 339; width: 306; height: 76; radius: 4; normalColor:theme.background; text: "0"; textSize: 32; onClicked: pad.key("0") }
        TouchButton { objectName: "keyMinus"; x: 321; y: 339; width: 148; height: 76; radius: 4; normalColor:theme.background; iconName: "minus"; iconSize: 64; onClicked: pad.key("-") }
        TouchButton { objectName: "keyLeft"; x: 5; y: 425; width: 148; height: 76; radius: 4; normalColor: theme.light ? theme.raised : "#3D403D"; iconName: "left"; onClicked: pad.key("left") }
        TouchButton { objectName: "keyRight"; x: 163; y: 425; width: 148; height: 76; radius: 4; normalColor: theme.light ? theme.raised : "#3D403D"; iconName: "right"; onClicked: pad.key("right") }
        TouchButton { objectName: "keyDecimal"; x: 321; y: 425; width: 148; height: 76; radius: 4; normalColor: theme.light ? theme.raised : "#3D403D"; text: "."; onClicked: pad.key(".") }
        TouchButton { objectName: "keyCancel"; x: 482; y: 425; width: 148; height: 76; normalColor: "#A92621"; iconName: "close"; onClicked: pad.key("close") }
    }
}
