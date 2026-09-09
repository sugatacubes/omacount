import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "Model.js" as Model

BarWidget {
  id: root
  moduleName: "omameter.activity"

  property bool popupOpen: false
  property var stats: ({ totals: {}, collector: {}, per_key: {}, shortcuts: {} })
  property var preferences: ({ paused: false, unit: "meters", custom_unit: {}, metrics: {} })
  readonly property string home: Quickshell.env("HOME")
  readonly property string stateHome: Quickshell.env("XDG_STATE_HOME") || home + "/.local/state"
  readonly property string configHome: Quickshell.env("XDG_CONFIG_HOME") || home + "/.config"
  readonly property string statsPath: stateHome + "/omameter/stats.json"
  readonly property string settingsPath: configHome + "/omameter/settings.json"
  readonly property string controlPath: home + "/.local/bin/omameterctl"
  readonly property var totals: stats && stats.totals ? stats.totals : ({})
  readonly property bool healthy: stats && stats.collector && stats.collector.permission_ok === true
  readonly property bool opened: popupOpen

  function parseJson(raw, fallback) {
    try { return JSON.parse(String(raw || "")) }
    catch (e) { return fallback }
  }

  function open() {
    statsFile.reload()
    settingsFile.reload()
    popupOpen = true
  }
  function close() { popupOpen = false }
  function togglePanel() { popupOpen ? close() : open() }
  function showPage(page) {
    dashboard.page = Math.max(0, Math.min(2, Number(page)))
    open()
  }
  function showKeyboardDetail(detail) {
    dashboard.showKeyboardDetail(detail)
    open()
  }
  function command(args) {
    var command = [controlPath]
    for (var i = 0; i < args.length; i++) command.push(String(args[i]))
    Quickshell.execDetached(command)
  }

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  FileView {
    id: statsFile
    path: root.statsPath
    watchChanges: true
    atomicWrites: true
    printErrors: false
    onLoaded: root.stats = root.parseJson(text(), root.stats)
    onFileChanged: reload()
  }

  FileView {
    id: settingsFile
    path: root.settingsPath
    watchChanges: true
    atomicWrites: true
    printErrors: false
    onLoaded: root.preferences = root.parseJson(text(), root.preferences)
    onFileChanged: reload()
  }

  Component {
    id: omameterMark

    Item {
      opacity: root.preferences.paused ? 0.48 : 1

      Text {
        anchors.centerIn: parent
        anchors.horizontalCenterOffset: -Style.spaceReal(1)
        text: "󰌌"
        color: root.bar ? root.bar.barForeground : Color.foreground
        font.family: root.bar ? root.bar.fontFamily : Style.font.family
        font.pixelSize: Style.spaceReal(17)
      }

      Text {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.rightMargin: -Style.spaceReal(1)
        anchors.bottomMargin: -Style.spaceReal(1)
        text: "󰍽"
        color: root.healthy ? (root.bar ? root.bar.barForeground : Color.foreground) : Color.accent
        font.family: root.bar ? root.bar.fontFamily : Style.font.family
        font.pixelSize: Style.spaceReal(9)
        font.bold: true
      }
    }
  }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: ""
    iconComponent: omameterMark
    tooltipText: root.preferences.paused
      ? "Omameter paused · click to inspect · right-click to resume"
      : root.healthy
        ? "Omameter · " + Model.compact(root.totals.keys_pressed) + " keys · "
          + Model.formatDistance(root.totals.pointer_distance_mm, root.preferences)
        : "Omameter needs input permission · click for details"
    onPressed: function(b) {
      if (b === Qt.RightButton) root.command([root.preferences.paused ? "resume" : "pause"])
      else root.togglePanel()
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.popupOpen
    centerOnBar: true
    focusTarget: dashboard
    contentWidth: panel.fittedContentWidth(Style.space(860))
    contentHeight: panel.fittedContentHeight(dashboard.implicitHeight, Style.space(700))

    Dashboard {
      id: dashboard
      anchors.fill: parent
      stats: root.stats
      settings: root.preferences
      foreground: root.bar ? root.bar.foreground : Color.foreground
      accent: Color.accent
      onCommand: function(args) { root.command(args) }
      onCloseRequested: root.close()
    }
  }

  IpcHandler {
    target: "omameter.activity"
    function open(): void { root.open() }
    function close(): void { root.close() }
    function show(): void { root.open() }
    function hide(): void { root.close() }
    function toggle(): void { root.togglePanel() }
    function pointer(): void { root.showPage(0) }
    function keyboard(): void { root.showPage(1) }
    function shortcuts(): void { root.showKeyboardDetail(1) }
    function heatmap(): void { root.showKeyboardDetail(2) }
    function settings(): void { root.showPage(2) }
    function pause(): void { root.command(["pause"]) }
    function resume(): void { root.command(["resume"]) }
  }
}
