import QtQuick
import QtQuick.Controls

ComboBox {
    id: choice
    property string navLabel: "Choose option"
    property string navKind: "choice"
    function stepFromKnob(amount) {
        if(!count)return
        activated((currentIndex+amount%count+count)%count)
    }
    implicitHeight:48
    font.family:theme.fontFamily
    font.pixelSize:20
    palette.button:theme.light?"#D7DAD7":"#353535"
    palette.buttonText:theme.foreground
    palette.text:theme.foreground
    palette.base:theme.light?"#E2E4E2":"#303030"
    palette.window:theme.light?"#E2E4E2":"#303030"
    palette.windowText:theme.foreground
    palette.highlight:theme.active
    palette.highlightedText:theme.activeInk
    Accessible.name:navLabel
    popup.height:Math.min(340,popup.contentItem.implicitHeight)
}
