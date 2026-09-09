import QtQuick
import qs.Commons
import qs.Ui
import "Model.js" as Model

Item {
  id: root

  property var perKey: ({})
  property color foreground: Color.foreground
  property color accent: Color.accent
  property string hoveredLabel: "Typed keys only · hover for the exact count"
  readonly property real unit: Style.space(43)
  readonly property real gap: Style.space(5)
  readonly property real maximum: Model.maxKeyCount(perKey)
  readonly property var rows: [
    [
      {id:"KEY_ESC",label:"ESC",w:1}, {id:"KEY_F1",label:"F1",w:1}, {id:"KEY_F2",label:"F2",w:1},
      {id:"KEY_F3",label:"F3",w:1}, {id:"KEY_F4",label:"F4",w:1}, {id:"KEY_F5",label:"F5",w:1},
      {id:"KEY_F6",label:"F6",w:1}, {id:"KEY_F7",label:"F7",w:1}, {id:"KEY_F8",label:"F8",w:1},
      {id:"KEY_F9",label:"F9",w:1}, {id:"KEY_F10",label:"F10",w:1}, {id:"KEY_F11",label:"F11",w:1},
      {id:"KEY_F12",label:"F12",w:1}
    ],
    [
      {id:"KEY_GRAVE",label:"`",w:1}, {id:"KEY_1",label:"1",w:1}, {id:"KEY_2",label:"2",w:1},
      {id:"KEY_3",label:"3",w:1}, {id:"KEY_4",label:"4",w:1}, {id:"KEY_5",label:"5",w:1},
      {id:"KEY_6",label:"6",w:1}, {id:"KEY_7",label:"7",w:1}, {id:"KEY_8",label:"8",w:1},
      {id:"KEY_9",label:"9",w:1}, {id:"KEY_0",label:"0",w:1}, {id:"KEY_MINUS",label:"−",w:1},
      {id:"KEY_EQUAL",label:"=",w:1}, {id:"KEY_BACKSPACE",label:"⌫",w:1.65}
    ],
    [
      {id:"KEY_TAB",label:"TAB",w:1.45}, {id:"KEY_Q",label:"Q",w:1}, {id:"KEY_W",label:"W",w:1},
      {id:"KEY_E",label:"E",w:1}, {id:"KEY_R",label:"R",w:1}, {id:"KEY_T",label:"T",w:1},
      {id:"KEY_Y",label:"Y",w:1}, {id:"KEY_U",label:"U",w:1}, {id:"KEY_I",label:"I",w:1},
      {id:"KEY_O",label:"O",w:1}, {id:"KEY_P",label:"P",w:1}, {id:"KEY_LEFTBRACE",label:"[",w:1},
      {id:"KEY_RIGHTBRACE",label:"]",w:1}, {id:"KEY_BACKSLASH",label:"\\",w:1.2}
    ],
    [
      {id:"KEY_CAPS_LOCK",label:"CAPS",w:1.75}, {id:"KEY_A",label:"A",w:1}, {id:"KEY_S",label:"S",w:1},
      {id:"KEY_D",label:"D",w:1}, {id:"KEY_F",label:"F",w:1}, {id:"KEY_G",label:"G",w:1},
      {id:"KEY_H",label:"H",w:1}, {id:"KEY_J",label:"J",w:1}, {id:"KEY_K",label:"K",w:1},
      {id:"KEY_L",label:"L",w:1}, {id:"KEY_SEMICOLON",label:";",w:1}, {id:"KEY_APOSTROPHE",label:"'",w:1},
      {id:"KEY_ENTER",label:"ENTER",w:2.05}
    ],
    [
      {id:"KEY_LEFT_SHIFT",label:"SHIFT",w:2.15}, {id:"KEY_Z",label:"Z",w:1}, {id:"KEY_X",label:"X",w:1},
      {id:"KEY_C",label:"C",w:1}, {id:"KEY_V",label:"V",w:1}, {id:"KEY_B",label:"B",w:1},
      {id:"KEY_N",label:"N",w:1}, {id:"KEY_M",label:"M",w:1}, {id:"KEY_COMMA",label:",",w:1},
      {id:"KEY_DOT",label:".",w:1}, {id:"KEY_SLASH",label:"/",w:1}, {id:"KEY_RIGHT_SHIFT",label:"SHIFT",w:2.15}
    ],
    [
      {id:"KEY_LEFT_CTRL",label:"CTRL",w:1.35}, {id:"KEY_LEFTMETA",label:"SUPER",w:1.35},
      {id:"KEY_LEFT_ALT",label:"ALT",w:1.25}, {id:"KEY_SPACE",label:"SPACE",w:6.2},
      {id:"KEY_RIGHT_ALT",label:"ALT",w:1.25}, {id:"KEY_COMPOSE",label:"MENU",w:1.25},
      {id:"KEY_RIGHT_CTRL",label:"CTRL",w:1.35}
    ]
  ]

  function countFor(id) { return Number(perKey && perKey[id] || 0) }

  implicitHeight: header.implicitHeight + Style.space(12) + keyboard.implicitHeight

  Text {
    id: header
    anchors.top: parent.top
    anchors.horizontalCenter: parent.horizontalCenter
    text: root.hoveredLabel
    color: Qt.darker(root.foreground, 1.35)
    font.family: Style.font.family
    font.pixelSize: Style.font.bodySmall
  }

  Column {
    id: keyboard
    anchors.top: header.bottom
    anchors.topMargin: Style.space(12)
    anchors.horizontalCenter: parent.horizontalCenter
    spacing: root.gap

    Repeater {
      model: root.rows

      Row {
        required property var modelData
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: root.gap

        Repeater {
          model: modelData

          BorderSurface {
            required property var modelData
            readonly property real keyCount: root.countFor(modelData.id)
            readonly property real intensity: Model.heat(keyCount, root.maximum)
            width: root.unit * Number(modelData.w || 1)
            height: Style.space(38)
            radius: Style.cornerRadius > 0 ? Style.space(6) : 0
            color: keyMouse.containsMouse
              ? Style.hoverFillFor(root.foreground, root.accent)
              : Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.04 + intensity * 0.72)
            borderSpec: Border.flat(Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b,
                                            keyMouse.containsMouse ? 0.48 : 0.13), Style.spacing.hairline)

            Text {
              anchors.centerIn: parent
              text: modelData.label
              color: keyMouse.containsMouse
                ? Style.hoverStateColor(root.foreground, root.accent) : root.foreground
              font.family: Style.font.family
              font.pixelSize: String(modelData.label).length > 3 ? Style.font.caption : Style.font.bodySmall
              font.bold: keyCount > 0
            }

            MouseArea {
              id: keyMouse
              anchors.fill: parent
              hoverEnabled: true
              acceptedButtons: Qt.NoButton
              onEntered: root.hoveredLabel = modelData.label + "  ·  " + Math.round(parent.keyCount) + " presses"
              onExited: root.hoveredLabel = "Typed keys only · hover for the exact count"
            }
          }
        }
      }
    }
  }
}
