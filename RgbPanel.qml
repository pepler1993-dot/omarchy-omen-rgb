import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

Panel {
    id: root
    moduleName: "kevin.omen-rgb"
    manageIpc: false
    property var anchorItem: null
    property var hostWidget: null
    property var colors: ["FFFFFF", "FFFFFF", "FFFFFF", "FFFFFF"]
    property int brightness: 100
    property int selectedZone: -1
    property bool available: false
    property bool writable: false
    property bool dirty: false
    property string message: "RGB wird geprüft …"
    readonly property string scriptPath: Qt.resolvedUrl("rgb.py").toString().replace("file://", "")

    function open() { controller.show(); if (!dirty) run("status") }
    function switchPanel(direction) {
        return bar && typeof bar.switchPanelFrom === "function" ? bar.switchPanelFrom(hostWidget || root, direction) : false
    }
    function choose(color) {
        var clean = color.trim().replace(/^#/, "").toUpperCase()
        if (!/^[0-9A-F]{6}$/.test(clean)) {
            message = "Bitte sechs Hex-Zeichen eingeben, z. B. FF8800."
            return
        }
        var next = colors.slice()
        for (var i = 0; i < 4; i++) if (selectedZone < 0 || selectedZone === i) next[i] = clean
        colors = next
        dirty = true
    }
    function preset(values) { colors = values.slice(); dirty = true }
    function run(action) {
        if (backend.running) return
        var command = ["/usr/bin/python3", scriptPath, action]
        if (action === "apply") command = command.concat(["--colors"], colors, ["--brightness", String(brightness)])
        backend.command = command
        backend.running = true
    }
    Component.onCompleted: run("status")

    Process {
        id: backend
        stdout: StdioCollector {
            waitForEnd: true
            onStreamFinished: {
                try {
                    var result = JSON.parse(text)
                    root.message = result.message || ""
                    if (result.available !== undefined) {
                        root.available = result.available
                        root.writable = result.writable
                        root.colors = result.colors
                        root.brightness = result.brightness
                        root.dirty = false
                    }
                } catch (error) { root.message = "Die RGB-Steuerung hat keine gültige Antwort geliefert." }
            }
        }
        stderr: StdioCollector {
            waitForEnd: true
            onStreamFinished: if (text.trim()) root.message = text.trim()
        }
    }

    KeyboardPanel {
        id: panel
        anchorItem: root.anchorItem
        owner: root.hostWidget || root
        bar: root.bar
        open: root.opened
        focusTarget: keyCatcher
        contentWidth: panel.fittedContentWidth(Style.space(400))
        contentHeight: panel.fittedContentHeight(content.implicitHeight)

        PanelKeyCatcher {
            id: keyCatcher
            anchors.fill: parent
            onCloseRequested: root.close()
            onTabRequested: function(direction) { root.switchPanel(direction) }

            Column {
                id: content
                width: parent.width
                spacing: Style.space(12)
                Text {
                    text: "OMEN · Tastaturfarben"
                    color: root.barForeground
                    font.family: Style.font.family
                    font.pixelSize: Style.font.subtitle
                    font.bold: true
                }
                Text {
                    width: parent.width
                    text: root.message
                    wrapMode: Text.WordWrap
                    color: root.barForeground
                    font.family: Style.font.family
                    font.pixelSize: Style.font.bodySmall
                    opacity: 0.8
                }
                Row {
                    width: parent.width
                    spacing: Style.space(6)
                    Repeater {
                        model: 4
                        Rectangle {
                            required property int index
                            width: (parent.width - parent.spacing * 3) / 4
                            height: Style.space(58)
                            radius: Style.space(6)
                            color: "#" + root.colors[index]
                            opacity: 0.3 + root.brightness / 100 * 0.7
                            border.width: root.selectedZone === index ? 3 : 1
                            border.color: root.barForeground
                            Text {
                                anchors.centerIn: parent
                                text: index === 3 ? "WASD" : "Zone " + (index + 1)
                                color: parent.color.r * 0.299 + parent.color.g * 0.587 + parent.color.b * 0.114 > 0.55 ? "#161616" : "#FFFFFF"
                                font.family: Style.font.family
                                font.pixelSize: Style.font.bodySmall
                                font.bold: true
                            }
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.selectedZone = index
                            }
                        }
                    }
                }
                ButtonGroup {
                    options: [{value: "-1", label: "Alle"}, {value: "0", label: "1"}, {value: "1", label: "2"}, {value: "2", label: "3"}, {value: "3", label: "4"}]
                    value: String(root.selectedZone)
                    foreground: root.barForeground
                    onChanged: function(value) { root.selectedZone = Number(value) }
                }
                Flow {
                    width: parent.width
                    spacing: Style.space(8)
                    Repeater {
                        model: ["FFFFFF", "FF4040", "FF8800", "FFD43B", "53E87A", "35D9E8", "488CFF", "AB6AFF", "FF65BC", "000000"]
                        Rectangle {
                            required property string modelData
                            width: Style.space(28)
                            height: width
                            radius: width / 2
                            color: "#" + modelData
                            border.width: 1
                            border.color: root.barForeground
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.choose(modelData)
                            }
                        }
                    }
                }
                Row {
                    width: parent.width
                    spacing: Style.space(8)
                    TextField {
                        id: hexInput
                        width: parent.width - colorButton.width - parent.spacing
                        placeholderText: "Eigene Farbe · #FF8800"
                        maximumLength: 7
                        foreground: root.barForeground
                        onAccepted: root.choose(text)
                    }
                    Button {
                        id: colorButton
                        text: "Auswählen"
                        foreground: root.barForeground
                        onClicked: root.choose(hexInput.text)
                    }
                }
                Flow {
                    width: parent.width
                    spacing: Style.space(6)
                    Button { text: "Warmweiß"; foreground: root.barForeground; onClicked: root.choose("FFD6AA") }
                    Button { text: "Ozean"; foreground: root.barForeground; onClicked: root.preset(["124CFF", "008DFF", "00CDDB", "61F4D1"]) }
                    Button { text: "Abendrot"; foreground: root.barForeground; onClicked: root.preset(["FF4938", "FF8D38", "F44790", "8B45CF"]) }
                    Button { text: "Spektrum"; foreground: root.barForeground; onClicked: root.preset(["FF4040", "FFD43B", "53E87A", "488CFF"]) }
                    Button {
                        text: "Gaming RGB"
                        tooltipText: "Cyan, Violett und Pink · WASD in Orange"
                        foreground: root.barForeground
                        onClicked: {
                            root.preset(["00E5FF", "8000FF", "FF00CC", "FF8000"])
                            root.brightness = 100
                        }
                    }
                }
                PanelSeparator { foreground: root.barForeground }
                Text {
                    text: "Helligkeit · " + root.brightness + " %"
                    color: root.barForeground
                    font.family: Style.font.family
                    font.pixelSize: Style.font.body
                }
                PanelSlider {
                    width: parent.width
                    bar: root.bar
                    value: root.brightness
                    minimum: 0
                    maximum: 100
                    integer: true
                    step: 5
                    onMoved: function(value) { root.brightness = Math.round(value); root.dirty = true }
                }
                Row {
                    width: parent.width
                    spacing: Style.space(8)
                    Button {
                        text: "Neu einlesen"
                        foreground: root.barForeground
                        enabled: !backend.running
                        onClicked: root.run("status")
                    }
                    Button {
                        text: backend.running ? "Bitte warten …" : "Anwenden & speichern"
                        foreground: root.barForeground
                        enabled: root.available && root.writable && !backend.running
                        opacity: enabled ? 1 : 0.35
                        onClicked: root.run("apply")
                    }
                }
            }
        }
    }
}
