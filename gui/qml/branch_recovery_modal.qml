import QtQuick 2.12

Rectangle {
    id: root
    width: 780
    height: 540
    color: "#EEF2F8"

    property string selectedId: ""

    Rectangle {
        id: panel
        anchors.centerIn: parent
        width: 720
        height: 490
        radius: 14
        color: "#FFFFFF"
        border.color: "#D8E0EC"
        border.width: 1

        Column {
            anchors.fill: parent
            anchors.margins: 24
            spacing: 16

            Text {
                text: modalTitle
                font.pixelSize: 24
                font.bold: true
                color: "#15243A"
                wrapMode: Text.WordWrap
            }

            Text {
                text: modalMessage
                font.pixelSize: 14
                color: "#3A4F6B"
                wrapMode: Text.WordWrap
            }

            Rectangle {
                width: parent.width
                height: 1
                color: "#E4EBF4"
            }

            Rectangle {
                id: listContainer
                width: parent.width
                height: 280
                color: "#F8FAFD"
                border.color: "#E3EAF4"
                border.width: 1
                radius: 10

                Flickable {
                    anchors.fill: parent
                    anchors.margins: 10
                    contentWidth: width
                    contentHeight: listColumn.height
                    clip: true

                    Column {
                        id: listColumn
                        width: parent.width
                        spacing: 10

                        Repeater {
                            model: devicesModel
                            delegate: Rectangle {
                                width: listColumn.width
                                height: 74
                                radius: 10
                                color: root.selectedId === modelData.id ? "#DDEBFF" : "#FFFFFF"
                                border.color: root.selectedId === modelData.id ? "#4E88FF" : "#D8E0EC"
                                border.width: 1

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.selectedId = modelData.id
                                }

                                Column {
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    spacing: 4

                                    Text {
                                        text: modelData.mainLabel
                                        font.pixelSize: 15
                                        font.bold: true
                                        color: "#1B2D45"
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        text: modelData.subLabel
                                        font.pixelSize: 13
                                        color: "#4A607D"
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        text: "Estado: " + modelData.statusLabel
                                        font.pixelSize: 12
                                        color: "#5F7490"
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: "#E4EBF4"
            }

            Row {
                width: parent.width
                spacing: 10

                Rectangle {
                    width: (parent.width - 10) / 2
                    height: 44
                    radius: 10
                    color: "#F2F4F7"
                    border.color: "#D0D5DD"
                    border.width: 1

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: bridge.createNew()
                    }

                    Text {
                        anchors.centerIn: parent
                        text: "Crear nueva sucursal"
                        color: "#344054"
                        font.pixelSize: 14
                        font.bold: true
                    }
                }

                Rectangle {
                    width: (parent.width - 10) / 2
                    height: 44
                    radius: 10
                    color: root.selectedId !== "" ? "#2C6DFF" : "#9DB8EE"

                    MouseArea {
                        anchors.fill: parent
                        enabled: root.selectedId !== ""
                        cursorShape: root.selectedId !== "" ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: bridge.recoverSelection(root.selectedId)
                    }

                    Text {
                        anchors.centerIn: parent
                        text: "Recuperar seleccionada"
                        color: "#FFFFFF"
                        font.pixelSize: 14
                        font.bold: true
                    }
                }
            }
        }
    }
}

