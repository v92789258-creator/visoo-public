import QtQuick 2.12

Rectangle {
    id: root
    width: 900
    height: 700
    color: "transparent"

    property string queryText: ""
    property bool open: false

    function requestClose() {
        if (!root.open) return
        root.open = false
        closeTimer.restart()
    }

    Timer {
        id: closeTimer
        interval: 210
        repeat: false
        onTriggered: bridge.close()
    }

    Component.onCompleted: {
        // Start closed, then animate in.
        root.open = true
    }

    Rectangle {
        id: overlay
        anchors.fill: parent
        color: "#00000066"
        opacity: root.open ? 1 : 0

        MouseArea {
            anchors.fill: parent
            onClicked: root.requestClose()
        }

        Behavior on opacity {
            NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
        }
    }

    Rectangle {
        id: drawer
        width: Math.min(380, root.width * 0.92)
        height: root.height
        x: root.open ? (root.width - drawer.width) : root.width
        y: 0
        color: "#FFFFFF"

        MouseArea {
            anchors.fill: parent
            onClicked: {}
        }

        Behavior on x {
            NumberAnimation { duration: 210; easing.type: Easing.OutCubic }
        }

        Column {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 14

            Item {
                width: parent.width
                height: 36

                Rectangle {
                    id: closeBtn
                    width: 36
                    height: 36
                    radius: 8
                    color: "transparent"
                    anchors.right: parent.right
                    anchors.top: parent.top

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.requestClose()
                    }

                    Image {
                        id: closeIcon
                        anchors.centerIn: parent
                        width: 18
                        height: 18
                        source: "../icons/close.svg"
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                    }

                    Text {
                        anchors.centerIn: parent
                        visible: closeIcon.status !== Image.Ready
                        text: "X"
                        font.pixelSize: 14
                        font.bold: true
                        color: "#101828"
                    }
                }
            }

            Column {
                width: parent.width
                spacing: 6

                Text {
                    text: "VISO"
                    font.pixelSize: 18
                    font.bold: true
                    color: "#101828"
                }

                Text {
                    text: (deviceLabel ? deviceLabel : "") + (branchLabel ? ("  |  " + branchLabel) : "")
                    font.pixelSize: 12
                    color: "#667085"
                    wrapMode: Text.WordWrap
                }
            }

            Rectangle {
                width: parent.width
                height: 40
                radius: 8
                color: "#F2F4F7"
                border.color: "#EAECF0"
                border.width: 1

                TextInput {
                    id: searchInput
                    anchors.fill: parent
                    anchors.margins: 10
                    font.pixelSize: 13
                    color: "#101828"
                    text: root.queryText
                    onTextChanged: root.queryText = text
                    onAccepted: {
                        if (root.queryText.trim().length > 0) {
                            bridge.search(root.queryText.trim())
                        }
                    }
                }

                Text {
                    anchors.left: parent.left
                    anchors.leftMargin: 10
                    anchors.verticalCenter: parent.verticalCenter
                    visible: searchInput.text.length === 0
                    text: "Buscar..."
                    font.pixelSize: 13
                    color: "#98A2B3"
                }
            }

            Row {
                width: parent.width
                spacing: 10

                Rectangle {
                    width: (parent.width - 20) / 3
                    height: 34
                    radius: 8
                    color: "#EEF2FF"
                    border.color: "#E0EAFF"
                    border.width: 1

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: bridge.action("open_notifications")
                    }

                    Text {
                        anchors.centerIn: parent
                        text: "Avisos"
                        font.pixelSize: 12
                        font.bold: true
                        color: "#1D4ED8"
                    }
                }

                Rectangle {
                    width: (parent.width - 20) / 3
                    height: 34
                    radius: 8
                    color: "#ECFDF3"
                    border.color: "#D1FADF"
                    border.width: 1
                    visible: isMadre

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: bridge.action("manual_backup")
                    }

                    Text {
                        anchors.centerIn: parent
                        text: "Respaldo"
                        font.pixelSize: 12
                        font.bold: true
                        color: "#027A48"
                    }
                }

                Rectangle {
                    width: (parent.width - 20) / 3
                    height: 34
                    radius: 8
                    color: "#F2F4F7"
                    border.color: "#EAECF0"
                    border.width: 1

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: bridge.action("open_profile")
                    }

                    Text {
                        anchors.centerIn: parent
                        text: "Perfil"
                        font.pixelSize: 12
                        font.bold: true
                        color: "#344054"
                    }
                }
            }

            Rectangle {
                width: parent.width
                height: 1
                color: "#EAECF0"
            }

            Text {
                text: "Navegacion"
                font.pixelSize: 12
                font.bold: true
                color: "#667085"
            }

            Rectangle {
                width: parent.width
                height: Math.max(220, root.height - 260)
                color: "transparent"

                Flickable {
                    anchors.fill: parent
                    contentWidth: width
                    contentHeight: listCol.height
                    clip: true

                    Column {
                        id: listCol
                        width: parent.width
                        spacing: 14

                        Repeater {
                            model: menuModel
                            delegate: Column {
                                width: listCol.width
                                spacing: 8
                                property bool expanded: false

                                Item {
                                    width: parent.width
                                    height: 24

                                    MouseArea {
                                        id: sectionArea
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        cursorShape: Qt.PointingHandCursor
                                        onClicked: expanded = !expanded
                                    }

                                    Text {
                                        anchors.left: parent.left
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: modelData.label
                                        font.pixelSize: 12
                                        font.bold: true
                                        color: sectionArea.containsMouse ? "#475467" : "#667085"
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        anchors.right: parent.right
                                        anchors.verticalCenter: parent.verticalCenter
                                        text: expanded ? "v" : ">"
                                        font.pixelSize: 12
                                        font.bold: true
                                        color: "#98A2B3"
                                    }
                                }

                                Item {
                                    id: itemsWrap
                                    width: parent.width
                                    height: expanded ? itemsCol.implicitHeight : 0
                                    clip: true

                                    Behavior on height {
                                        NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
                                    }

                                    Column {
                                        id: itemsCol
                                        width: parent.width
                                        spacing: 8
                                        opacity: expanded ? 1 : 0

                                        Behavior on opacity {
                                            NumberAnimation { duration: 140; easing.type: Easing.OutCubic }
                                        }

                                        Repeater {
                                            model: modelData.items
                                            delegate: Item {
                                                width: parent.width
                                                height: 26

                                                MouseArea {
                                                    id: linkArea
                                                    anchors.fill: parent
                                                    hoverEnabled: true
                                                    cursorShape: Qt.PointingHandCursor
                                                    onClicked: bridge.action(modelData.id)
                                                }

                                                Text {
                                                    id: linkText
                                                    anchors.left: parent.left
                                                    anchors.verticalCenter: parent.verticalCenter
                                                    width: parent.width
                                                    text: modelData.label
                                                    font.pixelSize: 13
                                                    font.bold: true
                                                    color: linkArea.containsMouse ? "#1D4ED8" : "#344054"
                                                    elide: Text.ElideRight
                                                }

                                                Rectangle {
                                                    height: 1
                                                    width: Math.min(linkText.implicitWidth, parent.width)
                                                    anchors.left: linkText.left
                                                    anchors.top: linkText.bottom
                                                    anchors.topMargin: 2
                                                    color: linkArea.containsMouse ? "#1D4ED8" : "#D0D5DD"
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
