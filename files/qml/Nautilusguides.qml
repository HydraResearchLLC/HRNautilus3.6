import QtQuick 2.1
import QtQuick.Controls 2.1
import QtQuick.Layouts 1.1
import QtQuick.Window 2.1
import QtQuick.Controls.Styles 1.1

import UM 1.1 as UM


UM.Dialog
{
    id: base
    property string installStatusText

    minimumWidth: 400 * screenScaleFactor
    minimumHeight: 350 * screenScaleFactor
    title: catalog.i18nc("@label", "3D Printing Guides & Troubleshooting")

    ColumnLayout {
      id: col1
      spacing: 10
      height: parent.height
      anchors.horizontalCenter: parent.horizontalCenter
      //anchors.fill: parent
          Rectangle {
            anchors.top: parent.top
            width: UM.Theme.getSize("toolbox_thumbnail_medium").width
            height: UM.Theme.getSize("toolbox_thumbnail_medium").height
            border.width: UM.Theme.getSize("default_lining").width
            border.color: UM.Theme.getColor("lining")

            Image {
              anchors.centerIn: parent
              width: UM.Theme.getSize("toolbox_thumbnail_medium").width - UM.Theme.getSize("wide_margin").width
              height: UM.Theme.getSize("toolbox_thumbnail_medium").height - UM.Theme.getSize("wide_margin").width
              source: "../img/design.png"
            }


          }
          Button {
                id: qualitybutton
                UM.I18nCatalog
                {
                    id: catalog
                    name: "cura"
                }
                anchors.margins: 10
                anchors.horizontalCenter: parent.horizontalCenter
                text: catalog1.i18nc("@action:button", "Open Print Quality Guide")
                onClicked: manager.openQualityGuide()
                //Layout.columnSpan:2
            }

            Button {
                id: designButton
                UM.I18nCatalog
                {
                    id: catalog1
                    name: "cura"
                }
                anchors.top: qualitybutton.bottom
                anchors.margins: 10
                //Layout.topMargin:25
                //topPadding: 5
                anchors.horizontalCenter: parent.horizontalCenter
                text: catalog.i18nc("@action:button", "Open Design Rules Guide")
                onClicked: manager.openDesignGuide()
                //Layout.columnSpan:2
            }

            Button {
                id: slicingButton
                UM.I18nCatalog
                {
                    id: catalog2
                    name: "cura"
                }
                anchors.top: designButton.bottom
                anchors.margins: 10
                //Layout.topMargin:25
                //topPadding: 5
                anchors.horizontalCenter: parent.horizontalCenter
                text: catalog.i18nc("@action:button", "Open Slicing Guide")
                onClicked: manager.openSlicingGuide()
                //Layout.columnSpan:2
            }

            Button {
                id: materialButton
                UM.I18nCatalog
                {
                    id: catalog3
                    name: "cura"
                }
                anchors.top: slicingButton.bottom
                anchors.margins: 10
                //Layout.topMargin:25
                //topPadding: 5
                anchors.horizontalCenter: parent.horizontalCenter
                text: catalog.i18nc("@action:button", "Open Material Guide")
                onClicked: manager.openMaterialGuide()
                //Layout.columnSpan:2
            }
        } // end RowLayout

    } // end ColumnLayout
