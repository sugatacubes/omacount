import QtQuick
import QtQuick.Layouts
import qs.Commons
import qs.Ui

Column {
  id: root

  property var settings: ({})
  property color foreground: Color.foreground
  property color accent: Color.accent
  signal command(var args)
  signal resetRequested()

  readonly property var custom: settings && settings.custom_unit ? settings.custom_unit : ({})
  readonly property var metricRows: [
    {key:"pointer_distance", label:"Cursor distance", description:"Total pointer and trackpad travel"},
    {key:"scroll_distance", label:"Scroll distance", description:"Estimated viewport travel"},
    {key:"active_time", label:"Active input time", description:"Keyboard and pointer activity"},
    {key:"rage_clicks", label:"Rage clicks", description:"Nearby rapid-click bursts"},
    {key:"average_scroll_speed", label:"Average scroll speed", description:"During scroll activity"},
    {key:"peak_scroll_speed", label:"Peak scroll speed", description:"Fastest scroll sample"},
    {key:"trackpad_presence", label:"Trackpad presence", description:"Detected through udev/libinput"},
    {key:"pointer_calories", label:"Pointer calories", description:"Mechanical-work estimate"},
    {key:"keys_pressed", label:"Keys pressed", description:"Focused-app typing presses"},
    {key:"shortcut_count", label:"Shortcut use", description:"Ctrl/Alt/Super chords"},
    {key:"average_wpm", label:"Average WPM", description:"Five-key word convention"},
    {key:"peak_wpm", label:"Peak WPM", description:"Best rolling minute"},
    {key:"accuracy", label:"Typed vs undone", description:"Backspace/Delete proxy"},
    {key:"typing_mouse_ratio", label:"Typing : mouse ratio", description:"Active-time comparison"},
    {key:"keyboard_calories", label:"Keyboard calories", description:"Mechanical-work estimate"}
  ]

  spacing: Style.space(14)

  Toggle {
    width: parent.width
    label: settings && settings.paused ? "Statistics paused" : "Statistics running"
    description: settings && settings.paused
      ? "Resume system-wide aggregate collection" : "Pause every counter immediately"
    checked: !(settings && settings.paused)
    foreground: root.foreground; accent: root.accent
    onClicked: root.command([settings && settings.paused ? "resume" : "pause"])
  }

  PanelSectionHeader { text: "DISTANCE UNITS"; foreground: root.foreground }

  Row {
    width: parent.width
    spacing: Style.space(12)

    Dropdown {
      width: Style.space(250)
      label: "Unit"
      value: String(root.settings && root.settings.unit || "meters")
      options: [
        {value:"meters", label:"Meters"}, {value:"miles", label:"Miles"},
        {value:"bananas", label:"Banana lengths"}, {value:"custom", label:"Custom"}
      ]
      foreground: root.foreground; accent: root.accent
      onChanged: function(value) { root.command(["set-unit", value]) }
    }

    Column {
      visible: root.settings && root.settings.unit === "custom"
      width: parent.width - Style.space(262)
      spacing: Style.space(7)
      Text {
        text: "1 custom unit equals this many meters"
        color: Qt.darker(root.foreground, 1.45); font.family: Style.font.family
        font.pixelSize: Style.font.caption; font.bold: true
      }
      Row {
        width: parent.width; spacing: Style.space(7)
        TextField {
          id: customName
          width: parent.width * 0.42
          text: String(root.custom.name || "")
          placeholderText: "Unit name"
          foreground: root.foreground; accent: root.accent
          onEditingFinished: root.command(["set-custom", text, customSymbol.text, customConversion.text])
        }
        TextField {
          id: customSymbol
          width: parent.width * 0.23
          text: String(root.custom.symbol || "")
          placeholderText: "Symbol"
          foreground: root.foreground; accent: root.accent
          onEditingFinished: root.command(["set-custom", customName.text, text, customConversion.text])
        }
        TextField {
          id: customConversion
          width: parent.width * 0.30
          text: String(root.custom.metres_per_unit || 1)
          placeholderText: "Meters"
          inputMethodHints: Qt.ImhFormattedNumbersOnly
          foreground: root.foreground; accent: root.accent
          onEditingFinished: root.command(["set-custom", customName.text, customSymbol.text, text])
        }
      }
    }
  }

  PanelSectionHeader { text: "VISIBLE METRICS"; foreground: root.foreground }

  Grid {
    id: toggleGrid
    width: parent.width
    columns: 2
    columnSpacing: Style.space(9)
    rowSpacing: Style.space(7)
    readonly property real cellWidth: (width - columnSpacing) / 2

    Repeater {
      model: root.metricRows
      Toggle {
        required property var modelData
        width: toggleGrid.cellWidth
        label: modelData.label
        description: modelData.description
        checked: !(root.settings && root.settings.metrics && root.settings.metrics[modelData.key] === false)
        foreground: root.foreground; accent: root.accent
        onClicked: root.command(["set-metric", modelData.key, checked ? "off" : "on"])
      }
    }
  }

  PanelSeparator { width: parent.width; foreground: root.foreground }

  Row {
    width: parent.width
    spacing: Style.space(12)
    Column {
      width: parent.width - resetButton.width - parent.spacing
      Text {
        text: "Privacy boundary"
        color: root.foreground; font.family: Style.font.family; font.pixelSize: Style.font.body; font.bold: true
      }
      Text {
        width: parent.width
        text: "Only counters are persisted. No text, passwords, clipboard, windows, applications, or key order."
        color: Qt.darker(root.foreground, 1.55); font.family: Style.font.family
        font.pixelSize: Style.font.caption; wrapMode: Text.WordWrap
      }
    }
    Button {
      id: resetButton
      text: "Reset statistics"; iconText: "󰑐"; foreground: Color.urgent
      bordered: true; onClicked: root.resetRequested()
    }
  }
}
