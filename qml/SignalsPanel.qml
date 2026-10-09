import QtQuick
import "Colors.js" as Colors

Item {
    id: dialog
    z:20
    property int channelIndex: 0
    property int side: 0
    property int revision: 0
    property bool axisPage: false
    property bool errorAxis: false
    property string tourMode:""
    property var chart: {revision;let c=ctl.channel(channelIndex).chart;if(tourMode){c=Object.assign({},c);c.mode=tourMode}return c}
    property string axisPrefix: errorAxis ? "chart_error_" : "chart_main_"
    signal editAxis(int index, string key, int side)
    function open(paneSide,index) {side=paneSide;channelIndex=index;axisPage=false;errorAxis=false;visible=true}
    Rectangle {objectName:"signalsScrim";x:dialog.side===0?800:0;y:0;width:800;height:720;color:"#000000";opacity:.76}
    MouseArea {anchors.fill:parent;onClicked:dialog.visible=false}
    Rectangle {
        id: panel;objectName:"signalsSurface"
        x:dialog.side===0?830:30;y:60;width:740;height:600
        radius:16;color:theme.light?"#F0F0F0":"#202020";border.width:0;clip:true
        MouseArea {anchors.fill:parent}
        TouchButton {objectName:"axisBack";ink:theme.light?theme.foreground:theme.active;x:12;y:14;width:54;height:54;visible:dialog.axisPage;iconName:"chevronLeft";iconSize:30;onClicked:dialog.axisPage=false}
        Text { font.family:theme.fontFamily;x:dialog.axisPage?74:28;y:24;text:(dialog.side===0?"Left":"Right")+" chart - "+theme.translate(theme.language,dialog.axisPage?"Y axis":"Signals");font.pixelSize: theme.fontSize(28);font.weight:Font.Medium;color:theme.light?theme.foreground:theme.active}
        TouchButton {objectName:"signalsClose";x:672;y:12;width:54;height:54;iconName:"close";iconSize:46;ink:theme.light?theme.foreground:theme.active;onClicked:dialog.visible=false}
        Rectangle {x:28;y:77;width:684;height:1;color:theme.light?"#BCBCBC":"#4B4B4B"}
        Item {
            id: pages;y:90;width:1480;height:500
            x: dialog.axisPage ? -740 : 0
            Behavior on x {enabled:dialog.visible;NumberAnimation {duration:240;easing.type:Easing.OutCubic}}
            Item {
                width:740;height:500
                ChoiceButton {objectName:"tabCombined";x:28;y:0;width:206;height:60;label:"Combined";symbol:"combined";activeChoice:dialog.chart.mode==="combined";onClicked:ctl.setChartMode(dialog.channelIndex,"combined")}
                ChoiceButton {objectName:"tabSplit";x:244;y:0;width:184;height:60;label:"Split";symbol:"split";activeChoice:dialog.chart.mode==="split";onClicked:ctl.setChartMode(dialog.channelIndex,"split")}
                ChoiceButton {objectName:"tabYAxis";x:544;y:0;width:168;height:60;label:"Y axis";symbol:"axis";onClicked:dialog.axisPage=true}
                Repeater {
                    model:2
                    Item {
                        required property int index
                        x:28;y:92+index*184;width:684;height:164
                        property bool errorSignal: index===1
                        property bool signalVisible: errorSignal?dialog.chart.errorVisible:dialog.chart.mainVisible
                        property bool upper: errorSignal?!dialog.chart.mainUpper:dialog.chart.mainUpper
                        Icon {x:0;y:4;width:34;height:30;ink:theme.light?theme.foreground:theme.active;kind:parent.errorSignal?"dashed":"minus"}
                        Text { font.family:theme.fontFamily;x:47;y:0;text:theme.translate(theme.language,parent.errorSignal?"Error":"Spectroscopy");font.pixelSize: theme.fontSize(28);color:theme.light?theme.foreground:theme.active}
                        Text { font.family:theme.fontFamily;x:47;y:40;text:parent.errorSignal?"Derived levels | Laser "+(dialog.channelIndex+1)+" | V | Required":"AFE"+(dialog.channelIndex+1)+" | Precision ADC | V | Required";font.pixelSize: theme.fontSize(18);color:theme.muted}
                        ToggleChoice {objectName:parent.errorSignal?"visibleError":"visibleMain";x:0;y:78;width:684;height:62;visible:dialog.chart.mode==="combined";label:parent.signalVisible?"Visible":"Hidden";symbol:parent.signalVisible?"eye":"eyeOff";activeChoice:parent.signalVisible;onClicked:ctl.toggleSignal(dialog.channelIndex,parent.errorSignal)}
                        Row {
                            x:0;y:78;spacing:12;visible:dialog.chart.mode==="split"
                            property bool errorSignal: parent.errorSignal
                            property bool upper: parent.upper
                            ChoiceButton {objectName:parent.errorSignal?"errorUpper":"mainUpper";width:336;height:62;label:"Upper";symbol:"up";activeChoice:parent.upper;onClicked:ctl.placeSignal(dialog.channelIndex,parent.errorSignal,true)}
                            ChoiceButton {objectName:parent.errorSignal?"errorLower":"mainLower";width:336;height:62;label:"Lower";symbol:"down";activeChoice:!parent.upper;onClicked:ctl.placeSignal(dialog.channelIndex,parent.errorSignal,false)}
                        }
                    }
                }
            }
            Item {
                x:740;width:740;height:500
                ChoiceButton {objectName:"axisMain";x:28;y:0;width:336;height:54;label:"Main";symbol:"minus";activeChoice:!dialog.errorAxis;onClicked:dialog.errorAxis=false}
                ChoiceButton {objectName:"axisError";x:376;y:0;width:336;height:54;label:"Error";symbol:"dashed";activeChoice:dialog.errorAxis;onClicked:dialog.errorAxis=true}
                Repeater {
                    model:2
                    Item {
                        required property int index
                        x:28;y:76+index*118;width:684;height:108
                        property string key: dialog.axisPrefix+(index===0?"scale":"position")
                        property real value: {dialog.revision;return ctl.value(dialog.channelIndex,key)}
                        Text { font.family:theme.fontFamily;text:parent.index===0?"Scale · V/div":"Position · centre voltage (V)";font.pixelSize: theme.fontSize(21);color:theme.light?theme.foreground:theme.active}
                        TouchButton {objectName:parent.index===0?"scaleMinus":"positionMinus";ink:theme.light?theme.foreground:theme.active;x:0;y:34;width:76;height:64;radius:8;normalColor:theme.light?"#E3E3E3":"#2B2B2B";iconName:"minus";iconSize:44;onClicked:ctl.stepAxis(dialog.channelIndex,parent.key,-1)}
                        TouchButton {objectName:parent.index===0?"scaleInput":"positionInput";ink:theme.light?theme.foreground:theme.active;x:88;y:34;width:508;height:64;radius:8;normalColor:theme.light?"#F8F8F8":"#171717";border.width:1;border.color:theme.light?"#AAAAAA":"#606060";text:Number(parent.value).toFixed(3);textSize:30;onClicked:dialog.editAxis(dialog.channelIndex,parent.key,dialog.side)}
                        TouchButton {objectName:parent.index===0?"scalePlus":"positionPlus";ink:theme.light?theme.foreground:theme.active;x:608;y:34;width:76;height:64;radius:8;normalColor:theme.light?"#E3E3E3":"#2B2B2B";iconName:"plus";iconSize:44;onClicked:ctl.stepAxis(dialog.channelIndex,parent.key,1)}
                    }
                }
                Text { font.family:theme.fontFamily;x:28;y:326;text:"Spectroscopy "+Math.round(dialog.chart.mainRatio*100)+"%";font.pixelSize: theme.fontSize(21);color:theme.light?theme.foreground:theme.active}
                Text { font.family:theme.fontFamily;x:470;y:326;width:242;horizontalAlignment:Text.AlignRight;text:"Error "+Math.round((1-dialog.chart.mainRatio)*100)+"%";font.pixelSize: theme.fontSize(21);color:theme.light?theme.foreground:theme.active}
                ReferenceSlider {
                    objectName:"heightRatio";x:28;y:358;width:684;height:60
                    minimum:20;maximum:80;value:dialog.chart.mainRatio*100
                    onMoved:function(value){ctl.setChartRatio(dialog.channelIndex,value/100)}
                }
                Text { font.family:theme.fontFamily;x:28;y:418;text:dialog.chart.mode==="combined"?"Split height ratio · applied when Split is selected":"Split height ratio · 20:80 to 80:20";font.pixelSize: theme.fontSize(17);color:theme.muted}
                ChoiceButton {objectName:"restoreAxes";x:28;y:452;width:684;height:48;label:"Restore defaults";symbol:"reset";onClicked:ctl.restoreChartAxes(dialog.channelIndex)}
            }
        }
    }
}
