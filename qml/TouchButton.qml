import QtQuick

Rectangle {
    id: button
    property string iconName: ""
    property string text: ""
    property color ink: "#F0F1EE"
    property color normalColor: "transparent"
    property bool selected: false
    property int iconSize: 52
    property int textSize: 24
    signal clicked()
    color: pointer.pressed ? "#454B44" : normalColor
    Accessible.role: Accessible.Button
    Accessible.name: text !== "" ? text : iconName
    Icon { anchors.centerIn: parent; width: button.iconSize; height: button.iconSize; visible: button.iconName !== ""; kind: button.iconName; ink: button.ink; active: button.selected }
    Text { anchors.centerIn: parent; text: button.text; visible: button.text !== ""; color: button.ink; font.pixelSize: button.textSize; font.family: "Roboto" }
    MouseArea { id: pointer; anchors.fill: parent; onClicked: button.clicked() }
}
