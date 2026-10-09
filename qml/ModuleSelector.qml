import QtQuick

Item {
    id: menu
    z:20
    property int channelIndex: 0
    property int side: 0
    property bool lower: false
    property bool modules: true
    property string selectedModule: "CC"
    property string selectedField: "current"
    property var entries: ctl.fields(selectedModule)
    signal closed
    function open(index, key, paneSide, bottom, showModules) {
        channelIndex = index;
        side = paneSide;
        lower = bottom;
        selectedField = key;
        selectedModule = ctl.parameter(key).module;
        modules = showModules;
        visible = true;
    }
    Rectangle {
        anchors.fill: parent
        color: theme.surface
        opacity: .77
    }
    MouseArea {
        anchors.fill: parent
        onClicked: menu.closed()
    }
    Item {
        x: menu.side === 0 ? 7 : 1177
        y: menu.lower ? Math.max(102, 620 - height) : 85
        width: 416
        height: menu.modules ? 194 : 44 + menu.entries.length * 87
        Canvas {
            id: moduleBackground
            Connections { target: theme; function onChanged() { moduleBackground.requestPaint(); } }
            anchors.fill: parent
            onVisibleChanged: if (visible)
                requestPaint()
            onAvailableChanged: if (available)
                requestPaint()
            onHeightChanged: requestPaint()
            onPaint: {
                let c = getContext("2d");
                c.reset();
                c.beginPath();
                c.moveTo(0, 27);
                c.lineTo(260, 27);
                c.lineTo(305, 0);
                c.lineTo(width, 0);
                c.lineTo(width, height);
                c.lineTo(0, height);
                c.closePath();
                c.fillStyle = theme.light ? theme.surface : "#040504";
                c.fill();
                c.strokeStyle = "#999C98";
                c.lineWidth = 2;
                c.stroke();
            }
        }
        Text { font.family:theme.fontFamily;
            x: 285
            y: 8
            width: 137
            text: theme.translate(theme.language,menu.selectedModule === "CC" ? "Current Control" : menu.selectedModule === "TC" ? "Temperature Control" : "Piezo Control")
            color: theme.foreground
            font.pixelSize: theme.fontSize(12)
            horizontalAlignment: Text.AlignHCenter
        }
        Row {
            x: 15
            y: 47
            spacing: 18
            visible: menu.modules
            Repeater {
                model: ["TC", "CC", "PC"]
                Rectangle {
                    required property string modelData
                    required property int index
                    width: 117
                    height: 122
                    color: menu.selectedModule === modelData ? (theme.light ? theme.raised : "#404040") : (theme.light ? theme.surface : "#151515")
                    Text { font.family:theme.fontFamily;
                        x: 18
                        y: 43
                        text: modelData
                        color: theme.foreground
                        font.pixelSize: theme.fontSize(36)
                    }
                    Text { font.family:theme.fontFamily;
                        x: 94
                        y: 20
                        text: index + 1
                        color: theme.foreground
                        font.pixelSize: theme.fontSize(12)
                    }
                    MouseArea {
                        objectName: "module" + modelData
                        property string navLabel: "Select " + modelData
                        anchors.fill: parent
                        onClicked: {
                            menu.selectedModule = modelData;
                            menu.modules = false;
                        }
                    }
                }
            }
        }
        Column {
            x: 15
            y: 43
            spacing: 19
            visible: !menu.modules
            Repeater {
                model: menu.entries
                Rectangle {
                    required property var modelData
                    width: 382
                    height: 68
                    color: menu.selectedField === modelData.key ? (theme.light ? theme.raised : "#404040") : (theme.light ? theme.surface : "#151515")
                    Text { font.family:theme.fontFamily;
                        x: 26
                        y: 16
                        width: 270
                        height: 36
                        text: theme.translate(theme.language,modelData.key === "temperature" ? "Set Temperature" : modelData.label)
                        color: theme.foreground
                        font.pixelSize: theme.fontSize(25)
                    }
                    Text { font.family:theme.fontFamily;
                        x: 275
                        y: 13
                        width: 94
                        height: 42
                        text: modelData.unit
                        color: theme.muted
                        font.pixelSize: theme.fontSize(30)
                        horizontalAlignment: Text.AlignHCenter
                    }
                    MouseArea {
                        objectName: "field" + modelData.key
                        property string navLabel: modelData.label
                        anchors.fill: parent
                        onClicked: {
                            ctl.selectField(menu.channelIndex, menu.lower, modelData.key);
                            menu.closed();
                        }
                    }
                }
            }
        }
    }
    TouchButton {
        objectName: "selectorCancel"
        x: menu.side === 0 ? 5 : 1509
        y: menu.lower ? 634 : 4
        width: 86
        height: 80
        normalColor: "#A92621"
        iconName: "close"
        onClicked: menu.closed()
    }
}
