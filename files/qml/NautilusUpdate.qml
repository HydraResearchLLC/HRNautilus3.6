import QtQuick 2.3
import QtQuick.Controls 1.4
import QtQuick.Controls.Styles 1.1
import QtQuick.Layouts 1.1
import QtQuick.Dialogs 1.3
import QtQuick.Window 2.1

import UM 1.2 as UM
import Cura 1.5 as Cura


Cura.MachineAction
{
    id: dialog;

    //property string currentName: (instanceList.currentIndex != -1 ? instanceList.currentItem.name : "");
    property int defaultVerticalMargin: UM.Theme.getSize("default_margin").height;
    property int defaultHorizontalMargin: UM.Theme.getSize("default_margin").width;
    property string selectedPath: CuraApplication.getDefaultPath("dialog_load_path")
    property bool validPath: false
    property bool connectedPrinter: true
    property int usefulWidth: 350 * screenScaleFactor


    Rectangle {
      width: parent.width + 20//- 20
      height: parent.height + 10000//(UM.Theme.getSize("toolbox_thumbnail_large").height * 1.5) + 20//5*parent.height/16 //UM.Theme.getSize("toolbox_thumbnail_large").height
      anchors.horizontalCenter: parent.horizontalCenter
      anchors.top: parent.top
      anchors.topMargin: - 10 // was 20
      border.width: UM.Theme.getSize("default_lining").width
      border.color: UM.Theme.getColor("lining")
    }
    Item {
        UM.I18nCatalog { id: catalog; name: "cura"; }
        SystemPalette { id: palette }
        id: windowFirmwareUpdate


        anchors {
            fill: parent;
            topMargin: parent.defaultVerticalMargin
                }
          Label{id: title; font: UM.Theme.getFont("large_bold"); text: "Update Firmware"}
          Label {id:instructions; anchors.top: title.bottom; anchors.topMargin: 20; text: "1. Select your printer from the dropdown menu\n2. Find NautilusFirmware.hrpp by typing the path or clicking Browse\n3. If your Nautilus is connected, press \"Update\". Your Nautilus will not be usable for the duration of the update." }
        GridLayout {
          id: printerRow;
          columns: 3
          rows: 5
          //spacing: 5;
          anchors { top: instructions.bottom
                    //left: printerRow.left
                    left: parent.left
                    right: parent.right
                    margins: 100
          }

          Label {id: selectLabel; Layout.row: 1; Layout.column: 1; text: "Select Printer: "}

          ComboBox{
              id: instanceList;
              Layout.row: 1;
              Layout.column: 2;
              anchors.verticalCenter: selectLabel.verticalCenter;
              model: manager.serverList;
              onCurrentIndexChanged: { dialog.connectedPrinter = manager.statusCheck(currentText);}
            }
          Label{
            text: "Status:"
            Layout.row: 2;
            Layout.column: 1;
          }
          Label {
            text: dialog.connectedPrinter ? "Ready" : "Disconnected";
            Layout.row: 2;
            Layout.column: 2;
            //visible: !dialog.connectedPrinter;
            font.bold: true

          }


          Label {Layout.row: 3; Layout.column: 1; text: "Firmware Zip: "}

          TextField {
                    id: pathField
                    placeholderText: "Enter path or click Browse"
                    text: fileDialog.fileUrl;
                    Layout.preferredWidth: usefulWidth;
                    Layout.row: 3;
                    Layout.column: 2;
                    onTextChanged: {
                        dialog.validPath = manager.validPath(pathField.text);
                      }
        }

          Cura.SecondaryButton {
            text: "Browse";
            Layout.row: 3;
            Layout.column: 3;
            onClicked: fileDialog.open()}

        Label{ text: "Invalid Path! ";
              Layout.row: 4;
              Layout.column: 2;
              visible: !dialog.validPath
      }
      }
      Label { anchors.bottom:updateButton.top;
              text: !dialog.validpath && !dialog.connectedPrinter ? "Invalid path and Nautilus not connected" : !dialog.validpath && dialog.connectedPrinter ? "Invalid path, but the printer is connected" :  "Printer disconnected, but the path is valid";
              visible: !(dialog.validPath && dialog.connectedPrinter);

            }

      Cura.PrimaryButton {
        id: updateButton
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        text: "Update"
        enabled: dialog.validPath && dialog.connectedPrinter
        onClicked: {confirmationDialog.open(); manager.setUpdatePrinter(instanceList.currentText);}
      }

        }

        Item
        {    UM.Dialog{
                id: confirmationDialog;
                minimumWidth: screenScaleFactor * 350
                minimumHeight: screenScaleFactor * 100
                Rectangle {
                  width: parent.width + 20//- 20
                  height: parent.height + 10000//(UM.Theme.getSize("toolbox_thumbnail_large").height * 1.5) + 20//5*parent.height/16 //UM.Theme.getSize("toolbox_thumbnail_large").height
                  anchors.horizontalCenter: parent.horizontalCenter
                  anchors.top: parent.top
                  anchors.topMargin: - 10 // was 20
                  border.width: UM.Theme.getSize("default_lining").width
                  border.color: UM.Theme.getColor("lining")
                }

                Label{
                  id: question
                  anchors.horizontalCenter: parent.horizontalCenter
                  text: "Begin updating your printer?"
                  font.bold: false
                  font.pointSize: 12
                  color: "#737373"
                  //Layout.columnSpan: 2
                }

                Cura.PrimaryButton{
                  id: button1
                  anchors.top: question.bottom
                  anchors.right: parent.horizontalCenter
                  anchors.topMargin: 20
                  anchors.rightMargin:10
                  text: "Yes"
                  onClicked: {confirmationDialog.close(), manager.updateConfirm()}
                }

                Cura.SecondaryButton{
                  id: button2
                  anchors.top: question.bottom
                  anchors.left: parent.horizontalCenter
                  anchors.topMargin: 20
                  anchors.leftMargin: 10
                  text: "No"
                  onClicked: {confirmationDialog.close()}
                }
            }
          }

        FileDialog {
          id: fileDialog
          title: "Please choose a file"
          folder: CuraApplication.getDefaultPath("dialog_load_path")
          nameFilters: [ "Zip files (*.zip)"]
          onAccepted: {
              selectedPath: fileDialog.fileUrl;
              manager.setZipPath(fileDialog.fileUrl);
              fileDialog.close();
          }
          onRejected: {
              fileDialog.close()
          }

}
}
