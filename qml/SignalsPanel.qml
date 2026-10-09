import QtQuick

Item {
    id: dialog
    property int channelIndex: 0
    property int side: 0
    property int revision: 0
    property bool axisPage: false
    property bool errorAxis: false
    property var chart: {revision;return ctl.channel(channelIndex).chart}
    property string axisPrefix: errorAxis ? "chart_error_" : "chart_main_"
    signal editAxis(int index, string key, int side)
    function open(paneSide,index) {side=paneSide;channelIndex=index;axisPage=false;errorAxis=false;visible=true}
    Rectangle {anchors.fill:parent;color:"#000000";opacity:.24}
    MouseArea {anchors.fill:parent;onClicked:dialog.visible=false}
    Rectangle {
        id: panel;objectName:"signalsSurface"
        x:dialog.side===0?850:10;y:106;width:740;height:600
        radius:16;color:"#151C17";border.color:"#687369";border.width:1;clip:true
        MouseArea {anchors.fill:parent}
        TouchButton {objectName:"axisBack";x:12;y:14;width:54;height:54;visible:dialog.axisPage;iconName:"chevronLeft";iconSize:30;onClicked:dialog.axisPage=false}
        Text {x:dialog.axisPage?74:28;y:24;text:(dialog.side===0?"Left":"Right")+" chart - "+(dialog.axisPage?"Y axis":"Signals");font.pixelSize:28;font.weight:Font.Medium;color:"#F0F1EE"}
        TouchButton {objectName:"signalsClose";x:672;y:12;width:54;height:54;iconName:"close";iconSize:46;onClicked:dialog.visible=false}
        Rectangle {x:28;y:77;width:684;height:1;color:"#424C43"}
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
                        Icon {x:0;y:4;width:34;height:30;kind:parent.errorSignal?"dashed":"minus"}
                        Text {x:47;y:0;text:parent.errorSignal?"Error":"Spectroscopy";font.pixelSize:28;color:"#F0F1EE"}
                        Text {x:47;y:40;text:parent.errorSignal?"Derived levels | Laser "+(dialog.channelIndex+1)+" | V | Required":"AFE"+(dialog.channelIndex+1)+" | Precision ADC | V | Required";font.pixelSize:18;color:"#B8C0B8"}
                        ChoiceButton {objectName:parent.errorSignal?"visibleError":"visibleMain";x:0;y:78;width:684;height:62;visible:dialog.chart.mode==="combined";label:parent.signalVisible?"Visible":"Hidden";symbol:parent.signalVisible?"eye":"eyeOff";activeChoice:parent.signalVisible;onClicked:ctl.toggleSignal(dialog.channelIndex,parent.errorSignal)}
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
                        Text {text:parent.index===0?"Scale · V/div":"Position · centre voltage (V)";font.pixelSize:21;color:"#CCD2CC"}
                        TouchButton {objectName:parent.index===0?"scaleMinus":"positionMinus";x:0;y:34;width:76;height:64;radius:8;normalColor:"#2B332D";iconName:"minus";iconSize:44;onClicked:ctl.stepAxis(dialog.channelIndex,parent.key,-1)}
                        TouchButton {objectName:parent.index===0?"scaleInput":"positionInput";x:88;y:34;width:508;height:64;radius:8;normalColor:"#080D09";border.width:1;border.color:"#58645A";text:Number(parent.value).toFixed(3);textSize:30;onClicked:dialog.editAxis(dialog.channelIndex,parent.key,dialog.side)}
                        TouchButton {objectName:parent.index===0?"scalePlus":"positionPlus";x:608;y:34;width:76;height:64;radius:8;normalColor:"#2B332D";iconName:"plus";iconSize:44;onClicked:ctl.stepAxis(dialog.channelIndex,parent.key,1)}
                    }
                }
                Text {x:28;y:326;text:"Spectroscopy "+Math.round(dialog.chart.mainRatio*100)+"%";font.pixelSize:21;color:"#D9D9D9"}
                Text {x:470;y:326;width:242;horizontalAlignment:Text.AlignRight;text:"Error "+Math.round((1-dialog.chart.mainRatio)*100)+"%";font.pixelSize:21;color:"#D9D9D9"}
                Item {
                    id:ratioControl;objectName:"heightRatio";x:28;y:358;width:684;height:60
                    Rectangle {x:18;y:26;width:648;height:8;radius:4;color:"#4C574E"}
                    Rectangle {x:18+(dialog.chart.mainRatio-.2)/.6*648-17;y:13;width:34;height:34;radius:17;color:"#D9D9D9"}
                    MouseArea {
                        anchors.fill:parent
                        function apply(x) {ctl.setChartRatio(dialog.channelIndex,.2+Math.max(0,Math.min(1,(x-18)/648))*.6)}
                        onPressed:function(mouse){apply(mouse.x)}
                        onPositionChanged:function(mouse){if(pressed)apply(mouse.x)}
                    }
                }
                Text {x:28;y:418;text:dialog.chart.mode==="combined"?"Split height ratio · applied when Split is selected":"Split height ratio · 20:80 to 80:20";font.pixelSize:17;color:"#B8C0B8"}
                ChoiceButton {objectName:"restoreAxes";x:28;y:452;width:684;height:48;label:"Restore defaults";symbol:"reset";onClicked:ctl.restoreChartAxes(dialog.channelIndex)}
            }
        }
    }
}
