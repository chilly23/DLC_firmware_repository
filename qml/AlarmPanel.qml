import QtQuick

/* Per-laser threshold editor opened from More.  It intentionally uses the
   same touch surfaces and numeric editor as the HMI parameter tiles. */
Item {
    id: dialog
    z:20
    property int channelIndex: 0
    property int side: 0
    property int revision: 0
    property var config: { revision; return ctl.alarm(channelIndex) }
    signal editRequested(int channelIndex, string key, int side, bool lower)

    function open(paneSide, index) {
        side = paneSide
        channelIndex = index
        visible = true
    }

    Rectangle {
        anchors.fill: parent
        color: "#000000"
        opacity: .76
    }
    MouseArea { anchors.fill: parent; onClicked: dialog.visible = false }

    Rectangle {
        id: panel
        x: dialog.side === 0 ? 830 : 30
        y: 52
        width: 740
        height: 616
        radius: 16
        color: theme.surface
        clip: true
        MouseArea { anchors.fill: parent }

        Text {
            x: 30; y: 22; width: 560; height: 44
            text: "Laser " + (dialog.channelIndex + 1) + " · Alarms"
            color: theme.foreground; font.family: theme.fontFamily
            font.pixelSize: theme.fontSize(29); font.weight: Font.Medium
        }
        TouchButton {
            x: 672; y: 12; width: 54; height: 54
            normalColor: "transparent"; iconName: "close"; iconSize: 42
            ink: theme.foreground; onClicked: dialog.visible = false
        }
        Rectangle { x: 28; y: 78; width: 684; height: 1; color: theme.raised }

        Flickable {
            id: scroller
            property string navLabel:"Scroll alarms and history"
            property string navKind:"slider"
            function stepFromKnob(delta){contentY=Math.max(0,Math.min(contentHeight-height,contentY+delta*60))}
            x: 0; y: 92; width: parent.width; height: 524
            contentWidth: width; contentHeight: column.height + 26
            clip: true; boundsBehavior: Flickable.StopAtBounds
            flickDeceleration: 2500; maximumFlickVelocity: 2600
            Column {
                id: column
                x: 28; width: 684; spacing: 15
                Text {
                    width: parent.width; wrapMode: Text.WordWrap
                    text: "Monitor live trace limits for this laser. Thresholds are saved with the instrument preferences."
                    color: theme.muted; font.family: theme.fontFamily
                    font.pixelSize: theme.fontSize(18)
                }
                Rectangle {
                    width: parent.width; height: 80; radius: 12; color: theme.raised
                    Text { x: 20; y: 15; text:theme.translate(theme.language,"Alarm monitoring"); color: theme.foreground; font.family: theme.fontFamily; font.pixelSize: theme.fontSize(23) }
                    Text { x: 20; y: 45; text: config.enabled ? "Threshold evaluation is active" : "Disabled · traces continue normally"; color: theme.muted; font.family: theme.fontFamily; font.pixelSize: theme.fontSize(16) }
                    Rectangle {
                        x: 582; y: 18; width: 82; height: 44; radius: 22
                        property string navLabel:"Alarm monitoring"
                        color: config.enabled ? theme.accent : "#4B554C"
                        Behavior on color { ColorAnimation { duration: 160 } }
                        Rectangle {
                            x: config.enabled ? 42 : 4; y: 4; width: 36; height: 36; radius: 18
                            color: "#FFFFFF"
                            Behavior on x { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }
                        }
                        MouseArea { anchors.fill: parent; onClicked: ctl.toggleAlarm(dialog.channelIndex) }
                    }
                }
                Repeater {
                    model: [
                        { title: "Spectroscopy high limit", key: "alarm_main_high", detail: "Alarm when the continuous trace exceeds this level." },
                        { title: "Error high limit", key: "alarm_error_high", detail: "Alarm when the derived error magnitude exceeds this level." }
                    ]
                    delegate: Rectangle {
                        required property var modelData
                        width: column.width; height: 112; radius: 12; color: theme.raised
                        Text { x: 20; y: 13; text:theme.translate(theme.language,modelData.title); color: theme.foreground; font.family: theme.fontFamily; font.pixelSize: theme.fontSize(22) }
                        Text { x: 20; y: 47; width: 420; wrapMode: Text.WordWrap; text: modelData.detail; color: theme.muted; font.family: theme.fontFamily; font.pixelSize: theme.fontSize(16) }
                        TouchButton {
                            x: 492; y: 22; width: 172; height: 66; radius: 9
                            normalColor: theme.active; ink: theme.activeInk
                            text: {dialog.revision; return Number(ctl.value(dialog.channelIndex, modelData.key)).toFixed(3) + " V"}
                            textSize: 23
                            onClicked: dialog.editRequested(dialog.channelIndex, modelData.key, dialog.side, false)
                        }
                    }
                }
                Rectangle {
                    width: parent.width; height: 92; radius: 12; color: theme.raised
                    Text { x: 20; y: 15; text:theme.translate(theme.language,"Alarm state"); color: theme.foreground; font.family: theme.fontFamily; font.pixelSize: theme.fontSize(22) }
                    Text {
                        x: 20; y: 48; width: parent.width-40
                        text:theme.translate(theme.language,config.status)
                        color: config.active ? "#FF453A" : theme.muted; font.family: theme.fontFamily
                        font.pixelSize: theme.fontSize(17)
                    }
                }
                Row {
                    spacing:12
                    TouchButton {objectName:"acknowledgeAlarm";width:336;height:60;radius:10;normalColor:theme.raised;text:theme.translate(theme.language,"Acknowledge");enabled:config.active&&!config.acknowledged;opacity:enabled?1:.45;onClicked:ctl.acknowledgeAlarm(dialog.channelIndex)}
                    TouchButton {objectName:"clearAlarmHistory";width:336;height:60;radius:10;normalColor:theme.raised;text:theme.translate(theme.language,"Clear history");onClicked:ctl.clearAlarmHistory(dialog.channelIndex)}
                }
                Text {text:theme.translate(theme.language,"History");font.family:theme.fontFamily;font.pixelSize:theme.fontSize(24);color:theme.foreground}
                Text {visible:config.events.length===0;text:theme.translate(theme.language,"No events");font.family:theme.fontFamily;font.pixelSize:theme.fontSize(18);color:theme.muted}
                Repeater {
                    model:config.events
                    Text {required property string modelData;width:column.width;text:modelData;wrapMode:Text.WordWrap;font.family:theme.fontFamily;font.pixelSize:theme.fontSize(18);color:theme.muted}
                }
            }
        }
    }
}
