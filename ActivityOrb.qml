import QtQuick
import qs.Commons
import qs.Ui

Item {
  id: root

  property real pointerShare: 0.5
  property bool paused: false
  property color foreground: Color.foreground
  property color accent: Color.accent

  width: Style.space(142)
  height: width

  Canvas {
    id: canvas
    anchors.fill: parent
    antialiasing: true
    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onPaint: {
      var ctx = getContext("2d")
      ctx.reset()
      var cx = width / 2, cy = height / 2
      var radius = Math.min(width, height) * 0.39
      var start = -Math.PI / 2
      var share = Math.max(0, Math.min(1, root.pointerShare))

      ctx.lineCap = Style.cornerRadius > 0 ? "round" : "butt"
      ctx.lineWidth = Style.space(9)
      ctx.strokeStyle = Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.10)
      ctx.beginPath(); ctx.arc(cx, cy, radius, 0, Math.PI * 2); ctx.stroke()

      ctx.strokeStyle = root.paused
        ? Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.34)
        : root.accent
      ctx.beginPath(); ctx.arc(cx, cy, radius, start, start + Math.PI * 2 * share); ctx.stroke()
    }
  }

  Connections {
    target: root
    function onPointerShareChanged() { canvas.requestPaint() }
    function onPausedChanged() { canvas.requestPaint() }
    function onForegroundChanged() { canvas.requestPaint() }
    function onAccentChanged() { canvas.requestPaint() }
  }

  Column {
    anchors.centerIn: parent
    spacing: Style.space(1)

    Text {
      anchors.horizontalCenter: parent.horizontalCenter
      text: root.paused ? "󰏤" : "󰍽"
      color: root.foreground
      font.family: Style.font.family
      font.pixelSize: Style.font.heading
    }
    Text {
      anchors.horizontalCenter: parent.horizontalCenter
      text: root.paused ? "PAUSED" : Math.round(root.pointerShare * 100) + "%"
      color: root.foreground
      font.family: Style.font.family
      font.pixelSize: Style.font.body
      font.bold: true
    }
    Text {
      anchors.horizontalCenter: parent.horizontalCenter
      text: "MOUSE SHARE"
      color: Qt.darker(root.foreground, 1.45)
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
      font.bold: true
      font.letterSpacing: 1
    }
  }

  MouseArea {
    id: orbMouse
    anchors.fill: parent
    hoverEnabled: true
    acceptedButtons: Qt.NoButton
  }

  PanelToolTip {
    visible: orbMouse.containsMouse
    text: "Mouse-active time as a share of mouse + typing active time"
    panelForeground: root.foreground
  }
}
