import QtQuick
import Quickshell
import qs.Commons
import qs.Ui

BarWidget {
    id: root
    moduleName: "kevin.omen-rgb"
    readonly property bool opened: popup.opened
    readonly property bool popoutSwitchClosing: popup.popoutSwitchClosing
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight
    function open() { popup.open() }
    function close() { popup.close() }
    function toggle() { popup.toggle() }
    function closeForPopoutSwitch() { popup.closeForPopoutSwitch() }

    RgbPanel {
        id: popup
        bar: root.bar
        settings: root.settings
        anchorItem: button
        hostWidget: root
    }

    WidgetButton {
        id: button
        anchors.fill: parent
        bar: root.bar
        text: "󰌌"
        active: root.opened
        tooltipText: "OMEN Tastaturfarben"
        horizontalMargin: 8.5
        onPressed: function(buttonCode) {
            if (buttonCode === Qt.LeftButton) root.toggle()
        }
    }
}
