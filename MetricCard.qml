import QtQuick
import qs.Commons
import qs.Ui

BorderSurface {
  id: root

  property string icon: ""
  property string label: ""
  property string value: "—"
  property string note: ""
  property color foreground: Color.foreground
  property color accent: Color.accent

  implicitHeight: Style.space(102)
  radius: Style.cornerRadius
  color: Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.035)
  borderSpec: Border.flat(Qt.rgba(root.foreground.r, root.foreground.g, root.foreground.b, 0.10), Style.spacing.hairline)
  padding: Style.space(13)

  Column {
    anchors.fill: parent
    anchors.topMargin: root.contentTopInset
    anchors.rightMargin: root.contentRightInset
    anchors.bottomMargin: root.contentBottomInset
    anchors.leftMargin: root.contentLeftInset
    spacing: Style.space(4)

    Row {
      width: parent.width
      spacing: Style.space(7)

      Text {
        text: root.icon
        color: Style.selectedStateColor(root.foreground, root.accent)
        font.family: Style.font.family
        font.pixelSize: Style.font.title
      }

      Text {
        width: parent.width - parent.children[0].implicitWidth - parent.spacing
        text: root.label.toUpperCase()
        color: Qt.darker(root.foreground, 1.55)
        font.family: Style.font.family
        font.pixelSize: Style.font.caption
        font.bold: true
        font.letterSpacing: 0.8
        elide: Text.ElideRight
      }
    }

    Text {
      width: parent.width
      text: root.value
      color: root.foreground
      font.family: Style.font.family
      font.pixelSize: Style.font.heading
      font.bold: true
      elide: Text.ElideRight
    }

    Text {
      visible: root.note !== ""
      width: parent.width
      text: root.note
      color: Qt.darker(root.foreground, 1.65)
      font.family: Style.font.family
      font.pixelSize: Style.font.caption
      elide: Text.ElideRight
    }
  }
}
