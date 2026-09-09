import QtQuick
import QtQuick.Controls
import qs.Commons
import qs.Ui
import "Model.js" as Model

Item {
  id: root

  property var stats: ({})
  property var settings: ({})
  property color foreground: Color.foreground
  property color accent: Color.accent
  property int detail: 0 // 0 summary, 1 shortcuts, 2 heatmap

  readonly property var totals: stats && stats.totals ? stats.totals : ({})
  readonly property var shortcutRows: Model.sortedShortcuts(stats && stats.shortcuts ? stats.shortcuts : ({}))

  implicitHeight: detail === 0 ? summary.implicitHeight : detailColumn.implicitHeight

  Column {
    id: summary
    visible: root.detail === 0
    width: parent.width
    spacing: Style.space(12)

    BorderSurface {
      id: keyboardHero
      width: parent.width
      height: Style.space(158)
      radius: Style.cornerRadius
      color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.035)
      borderSpec: Border.flat(Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.10), Style.spacing.hairline)
      padding: Style.space(18)

      Item {
        anchors.fill: parent
        anchors.topMargin: keyboardHero.contentTopInset
        anchors.rightMargin: keyboardHero.contentRightInset
        anchors.bottomMargin: keyboardHero.contentBottomInset
        anchors.leftMargin: keyboardHero.contentLeftInset

        Column {
          anchors.left: parent.left
          anchors.verticalCenter: parent.verticalCenter
          spacing: Style.space(4)
          Text {
            text: "KEYBOARD CONSTELLATION"
            color: Qt.darker(root.foreground, 1.5)
            font.family: Style.font.family; font.pixelSize: Style.font.caption
            font.bold: true; font.letterSpacing: 1.4
          }
          Text {
            text: Model.metricEnabled(root.settings, "keys_pressed")
              ? Model.compact(root.totals.keys_pressed) : "Metric hidden"
            color: root.foreground
            font.family: Style.font.family
            font.pixelSize: Model.metricEnabled(root.settings, "keys_pressed")
              ? Style.font.displayLarge : Style.font.title
            font.bold: true
          }
          Text {
            text: "typed key presses · shortcuts counted separately"
            color: Qt.darker(root.foreground, 1.5)
            font.family: Style.font.family; font.pixelSize: Style.font.body
          }
          Text {
            visible: Model.metricEnabled(root.settings, "keyboard_calories")
            text: "󰈸  " + Model.formatCalories(root.totals.keyboard_calories)
            color: root.accent
            font.family: Style.font.family; font.pixelSize: Style.font.caption; font.bold: true
          }
        }

        Column {
          anchors.right: parent.right
          anchors.verticalCenter: parent.verticalCenter
          width: Style.space(250)
          spacing: Style.space(8)

          Button {
            width: parent.width; text: "Shortcut breakdown"; iconText: "󰘳"
            foreground: root.foreground; bordered: true; leftAlign: true
            onClicked: root.detail = 1
          }
          Button {
            width: parent.width; text: "Keyboard heatmap"; iconText: "󰌌"
            foreground: root.foreground; bordered: true; leftAlign: true
            onClicked: root.detail = 2
          }
        }
      }
    }

    Grid {
      id: keyboardGrid
      width: parent.width
      columns: 3
      columnSpacing: Style.space(10)
      rowSpacing: Style.space(10)
      readonly property real cardWidth: (width - columnSpacing * 2) / 3

      MetricCard {
        width: keyboardGrid.cardWidth; foreground: root.foreground; accent: root.accent
        visible: Model.metricEnabled(root.settings, "shortcut_count")
        icon: "󰘳"; label: "Shortcuts"; value: Model.compact(root.totals.shortcut_count)
        note: "Ctrl, Alt or Super chords"
      }
      MetricCard {
        width: keyboardGrid.cardWidth; foreground: root.foreground; accent: root.accent
        visible: Model.metricEnabled(root.settings, "average_wpm")
        icon: "󰗚"; label: "Average WPM"; value: Number(root.totals.average_wpm || 0).toFixed(1)
        note: "5 keys per word"
      }
      MetricCard {
        width: keyboardGrid.cardWidth; foreground: root.foreground; accent: root.accent
        visible: Model.metricEnabled(root.settings, "peak_wpm")
        icon: "󰾆"; label: "Peak WPM"; value: Number(root.totals.peak_wpm || 0).toFixed(1)
        note: "best rolling minute"
      }
      MetricCard {
        width: keyboardGrid.cardWidth; foreground: root.foreground; accent: root.accent
        visible: Model.metricEnabled(root.settings, "accuracy")
        icon: "󰄬"; label: "Typed vs undone"; value: Number(root.totals.accuracy_percent || 0).toFixed(1) + "%"
        note: "printable keys vs Backspace/Delete"
      }
      MetricCard {
        width: keyboardGrid.cardWidth; foreground: root.foreground; accent: root.accent
        visible: Model.metricEnabled(root.settings, "typing_mouse_ratio")
        icon: "󰌌"; label: "Typing : mouse"; value: Model.ratioLabel(root.totals.typing_mouse_ratio)
        note: "active-time ratio"
      }
      MetricCard {
        width: keyboardGrid.cardWidth; foreground: root.foreground; accent: root.accent
        visible: Model.metricEnabled(root.settings, "keyboard_calories")
        icon: "󰈸"; label: "Typing energy"; value: Model.formatCalories(root.totals.keyboard_calories)
        note: "playful mechanical estimate"
      }
    }

  }

  Column {
    id: detailColumn
    visible: root.detail !== 0
    width: parent.width
    spacing: Style.space(12)

    Row {
      width: parent.width
      spacing: Style.space(10)
      Button {
        iconText: "󰁍"; text: "Back"; foreground: root.foreground; bordered: true
        onClicked: root.detail = 0
      }
      Text {
        anchors.verticalCenter: parent.verticalCenter
        text: root.detail === 1 ? "SHORTCUT BREAKDOWN" : "KEYBOARD HEATMAP"
        color: root.foreground; font.family: Style.font.family
        font.pixelSize: Style.font.title; font.bold: true; font.letterSpacing: 1
      }
    }

    BorderSurface {
      width: parent.width
      height: root.detail === 2 ? Style.space(360) : Style.space(390)
      radius: Style.cornerRadius
      color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.025)
      borderSpec: Border.flat(Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.10), Style.spacing.hairline)
      padding: Style.space(16)

      Heatmap {
        visible: root.detail === 2
        anchors.fill: parent
        anchors.topMargin: parent.contentTopInset
        anchors.rightMargin: parent.contentRightInset
        anchors.bottomMargin: parent.contentBottomInset
        anchors.leftMargin: parent.contentLeftInset
        perKey: root.stats && root.stats.per_key ? root.stats.per_key : ({})
        foreground: root.foreground; accent: root.accent
      }

      ListView {
        visible: root.detail === 1
        anchors.fill: parent
        anchors.topMargin: parent.contentTopInset
        anchors.rightMargin: parent.contentRightInset
        anchors.bottomMargin: parent.contentBottomInset
        anchors.leftMargin: parent.contentLeftInset
        clip: true
        spacing: Style.space(3)
        model: root.shortcutRows

        delegate: Rectangle {
          required property var modelData
          width: ListView.view.width
          height: Style.space(38)
          radius: Style.cornerRadius
          color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.035)
          Text {
            anchors.left: parent.left; anchors.leftMargin: Style.space(12); anchors.verticalCenter: parent.verticalCenter
            text: modelData.name; color: root.foreground; font.family: Style.font.family
            font.pixelSize: Style.font.body; font.bold: true
          }
          Text {
            anchors.right: parent.right; anchors.rightMargin: Style.space(12); anchors.verticalCenter: parent.verticalCenter
            text: Model.compact(modelData.count); color: root.accent; font.family: Style.font.family
            font.pixelSize: Style.font.body; font.bold: true
          }
        }

        Text {
          anchors.centerIn: parent
          visible: root.shortcutRows.length === 0
          text: "No shortcuts counted yet"
          color: Qt.darker(root.foreground, 1.55)
          font.family: Style.font.family; font.pixelSize: Style.font.body
        }
      }
    }
  }
}
