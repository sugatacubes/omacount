import QtQuick
import QtQuick.Controls
import Quickshell
import qs.Commons
import qs.Ui

Item {
  id: root

  property var stats: ({})
  property var settings: ({})
  property color foreground: Color.foreground
  property color accent: Color.accent
  property int page: 0
  signal command(var args)
  signal closeRequested()

  focus: true
  Keys.onEscapePressed: function(event) { root.closeRequested(); event.accepted = true }

  readonly property var collector: stats && stats.collector ? stats.collector : ({})
  readonly property bool healthy: collector.permission_ok === true
  readonly property string statusText: settings && settings.paused ? "PAUSED"
    : healthy ? "COLLECTING" : "PERMISSION NEEDED"
  readonly property real naturalHeight: heading.height + tabs.implicitHeight
    + pageHost.implicitHeight + Style.space(24)
    + (permissionBanner.visible ? permissionBanner.height + Style.space(12) : 0)

  implicitHeight: naturalHeight

  function showKeyboardDetail(detail) {
    root.page = 1
    keyboardPage.detail = Math.max(0, Math.min(2, Number(detail)))
  }

  Column {
    anchors.fill: parent
    spacing: Style.space(12)

    Item {
      id: heading
      width: parent.width
      height: Style.space(44)

      Row {
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        spacing: Style.space(10)
        Text {
          text: "󰇀"
          color: root.accent
          font.family: Style.font.family; font.pixelSize: Style.font.display
        }
        Column {
          anchors.verticalCenter: parent.verticalCenter
          spacing: 0
          Text {
            text: "OMAMETER"
            color: root.foreground
            font.family: Style.font.family; font.pixelSize: Style.font.heading
            font.bold: true; font.letterSpacing: 1.6
          }
          Text {
            text: "the quiet arithmetic of motion"
            color: Qt.darker(root.foreground, 1.65)
            font.family: Style.font.family; font.pixelSize: Style.font.caption
          }
        }
      }

      Row {
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        spacing: Style.space(7)
        Rectangle {
          width: statusRow.implicitWidth + Style.space(16)
          height: Style.space(28)
          radius: Style.cornerRadius > 0 ? height / 2 : 0
          color: Qt.rgba((root.healthy ? root.accent : Color.urgent).r,
                         (root.healthy ? root.accent : Color.urgent).g,
                         (root.healthy ? root.accent : Color.urgent).b, 0.12)
          Row {
            id: statusRow
            anchors.centerIn: parent
            spacing: Style.space(6)
            Rectangle {
              width: Style.space(6); height: width; radius: width / 2
              color: root.settings && root.settings.paused ? Qt.darker(root.foreground, 1.5)
                : root.healthy ? root.accent : Color.urgent
            }
            Text {
              text: root.statusText
              color: root.foreground; font.family: Style.font.family
              font.pixelSize: Style.font.caption; font.bold: true; font.letterSpacing: 0.7
            }
          }
        }
        Button {
          iconText: "󰅖"; tooltipText: "Close"; foreground: root.foreground
          onClicked: root.closeRequested()
        }
      }
    }

    Row {
      id: tabs
      width: parent.width
      spacing: Style.space(6)

      Repeater {
        model: [
          {label:"Pointer", icon:"󰍽"},
          {label:"Keyboard", icon:"󰌌"},
          {label:"Settings", icon:"󰒓"}
        ]
        Button {
          required property var modelData
          required property int index
          width: (tabs.width - tabs.spacing * 2) / 3
          text: modelData.label; iconText: modelData.icon
          foreground: root.foreground; active: root.page === index
          bordered: true; onClicked: root.page = index
        }
      }
    }

    Rectangle {
      id: permissionBanner
      visible: !root.healthy
      width: parent.width
      height: permissionText.implicitHeight + Style.space(18)
      radius: Style.cornerRadius
      color: Qt.rgba(Color.urgent.r, Color.urgent.g, Color.urgent.b, 0.11)
      border.color: Qt.rgba(Color.urgent.r, Color.urgent.g, Color.urgent.b, 0.42)
      border.width: Style.spacing.hairline
      Text {
        id: permissionText
        anchors.left: parent.left; anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: Style.space(12); anchors.rightMargin: Style.space(12)
        text: "Collector is installed but cannot read the selected input nodes. Run install.sh again or inspect: systemctl --user status omameter"
        color: root.foreground; font.family: Style.font.family; font.pixelSize: Style.font.caption
        wrapMode: Text.WordWrap
      }
    }

    Flickable {
      id: scroll
      width: parent.width
      height: parent.height - y
      contentWidth: width
      contentHeight: pageHost.implicitHeight
      clip: true
      boundsBehavior: Flickable.StopAtBounds
      interactive: contentHeight > height
      ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

      Item {
        id: pageHost
        width: scroll.width - (scroll.contentHeight > scroll.height ? Style.space(12) : 0)
        implicitHeight: Math.max(pointerPage.visible ? pointerPage.implicitHeight : 0,
                                 keyboardPage.visible ? keyboardPage.implicitHeight : 0,
                                 settingsPage.visible ? settingsPage.implicitHeight : 0) + Style.space(4)

        PointerPage {
          id: pointerPage
          visible: root.page === 0
          width: parent.width
          stats: root.stats; settings: root.settings
          foreground: root.foreground; accent: root.accent
        }

        KeyboardPage {
          id: keyboardPage
          visible: root.page === 1
          width: parent.width
          stats: root.stats; settings: root.settings
          foreground: root.foreground; accent: root.accent
        }

        SettingsPage {
          id: settingsPage
          visible: root.page === 2
          width: parent.width
          settings: root.settings
          foreground: root.foreground; accent: root.accent
          onCommand: function(args) { root.command(args) }
          onResetRequested: resetDialog.opened = true
        }
      }
    }
  }

  onPageChanged: {
    scroll.contentY = 0
    if (page !== 1) keyboardPage.detail = 0
  }

  ConfirmDialog {
    id: resetDialog
    anchors.fill: parent
    message: "Reset every Omameter aggregate? This cannot be undone. Your unit and visibility settings will be kept."
    confirmText: "Reset"
    foreground: root.foreground
    onCanceled: opened = false
    onConfirmed: {
      opened = false
      root.command(["reset"])
    }
  }
}
