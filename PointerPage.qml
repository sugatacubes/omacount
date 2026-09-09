import QtQuick
import qs.Commons
import qs.Ui
import "Model.js" as Model

Column {
  id: root

  property var stats: ({})
  property var settings: ({})
  property color foreground: Color.foreground
  property color accent: Color.accent

  readonly property var totals: stats && stats.totals ? stats.totals : ({})
  readonly property var collector: stats && stats.collector ? stats.collector : ({})
  readonly property bool paused: settings && settings.paused === true
  readonly property real totalInput: Number(totals.mouse_time_seconds || 0) + Number(totals.typing_time_seconds || 0)
  readonly property real pointerShare: totalInput > 0 ? Number(totals.mouse_time_seconds || 0) / totalInput : 0.5

  spacing: Style.space(12)

  BorderSurface {
    id: pointerHero
    width: parent.width
    height: Style.space(172)
    radius: Style.cornerRadius
    color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.035)
    borderSpec: Border.flat(Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.10), Style.spacing.hairline)
    padding: Style.space(18)

    Item {
      anchors.fill: parent
      anchors.topMargin: pointerHero.contentTopInset
      anchors.rightMargin: pointerHero.contentRightInset
      anchors.bottomMargin: pointerHero.contentBottomInset
      anchors.leftMargin: pointerHero.contentLeftInset

      Column {
        anchors.left: parent.left
        anchors.right: orb.left
        anchors.rightMargin: Style.space(18)
        anchors.verticalCenter: parent.verticalCenter
        spacing: Style.space(5)

        Text {
          text: "POINTER ORBIT"
          color: Qt.darker(root.foreground, 1.5)
          font.family: Style.font.family
          font.pixelSize: Style.font.caption
          font.bold: true
          font.letterSpacing: 1.4
        }
        Text {
          width: parent.width
          text: Model.metricEnabled(root.settings, "pointer_distance")
            ? Model.formatDistance(root.totals.pointer_distance_mm, root.settings) : "Metric hidden"
          color: root.foreground
          font.family: Style.font.family
          font.pixelSize: Model.metricEnabled(root.settings, "pointer_distance")
            ? Style.font.displayLarge : Style.font.title
          font.bold: true
          elide: Text.ElideRight
        }
        Text {
          width: parent.width
          text: "travelled across every app"
          color: Qt.darker(root.foreground, 1.5)
          font.family: Style.font.family
          font.pixelSize: Style.font.body
        }
        Text {
          width: parent.width
          text: "Ring = mouse share of mouse + typing active time"
          color: Qt.darker(root.foreground, 1.65)
          font.family: Style.font.family
          font.pixelSize: Style.font.caption
          elide: Text.ElideRight
        }
        Row {
          spacing: Style.space(8)
          Text {
            text: root.collector.trackpad_present ? "󰟸  TRACKPAD ONLINE" : "󰍽  NO TRACKPAD"
            visible: Model.metricEnabled(root.settings, "trackpad_presence")
            color: root.collector.trackpad_present ? root.accent : Qt.darker(root.foreground, 1.55)
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
            font.bold: true
          }
          Text {
            text: "·  " + Model.formatCalories(root.totals.pointer_calories)
            visible: Model.metricEnabled(root.settings, "pointer_calories")
            color: Qt.darker(root.foreground, 1.45)
            font.family: Style.font.family
            font.pixelSize: Style.font.caption
          }
        }
      }

      ActivityOrb {
        id: orb
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        pointerShare: root.pointerShare
        paused: root.paused
        foreground: root.foreground
        accent: root.accent
      }
    }
  }

  Grid {
    id: metricsGrid
    width: parent.width
    columns: 3
    columnSpacing: Style.space(10)
    rowSpacing: Style.space(10)

    readonly property real cardWidth: (width - columnSpacing * 2) / 3

    MetricCard {
      width: metricsGrid.cardWidth; foreground: root.foreground; accent: root.accent
      visible: Model.metricEnabled(root.settings, "scroll_distance")
      icon: "󰹹"; label: "Scroll distance"
      value: Model.formatDistance(root.totals.scroll_distance_mm, root.settings)
      note: "estimated viewport travel"
    }
    MetricCard {
      width: metricsGrid.cardWidth; foreground: root.foreground; accent: root.accent
      visible: Model.metricEnabled(root.settings, "active_time")
      icon: "󰔛"; label: "Active input"
      value: Model.formatDuration(root.totals.active_time_seconds)
      note: "5-second activity windows"
    }
    MetricCard {
      width: metricsGrid.cardWidth; foreground: root.foreground; accent: root.accent
      visible: Model.metricEnabled(root.settings, "rage_clicks")
      icon: "󰳽"; label: "Rage clicks"
      value: Model.compact(root.totals.rage_clicks)
      note: "3 nearby clicks in 0.8s"
    }
    MetricCard {
      width: metricsGrid.cardWidth; foreground: root.foreground; accent: root.accent
      visible: Model.metricEnabled(root.settings, "average_scroll_speed")
      icon: "󰓅"; label: "Average scroll"
      value: Model.formatSpeed(root.totals.average_scroll_speed_mm_s, root.settings)
      note: "while actively scrolling"
    }
    MetricCard {
      width: metricsGrid.cardWidth; foreground: root.foreground; accent: root.accent
      visible: Model.metricEnabled(root.settings, "peak_scroll_speed")
      icon: "󰾆"; label: "Peak scroll"
      value: Model.formatSpeed(root.totals.peak_scroll_speed_mm_s, root.settings)
      note: "fastest input sample"
    }
    MetricCard {
      width: metricsGrid.cardWidth; foreground: root.foreground; accent: root.accent
      visible: Model.metricEnabled(root.settings, "pointer_calories")
      icon: "󰈸"; label: "Input energy"
      value: Model.formatCalories(root.totals.pointer_calories)
      note: "playful mechanical estimate"
    }
  }

  Text {
    anchors.right: parent.right
    text: root.collector.distance_calibration === "edid-physical-size" ? "EDID calibrated" : "96-DPI fallback"
    color: Qt.darker(root.foreground, 1.75)
    font.family: Style.font.family
    font.pixelSize: Style.font.caption
  }
}
