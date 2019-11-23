import QtQuick 2.10
import QtQuick.Controls 2.3
import QtQuick.Window 2.2

import UM 1.3 as UM
import Cura 1.1 as Cura


//
// This component contains the content for the "Welcome" page of the welcome on-boarding process.
//
Window
{
    id: base;

    title: dialogTitle;
    flags: Qt.Dialog
    minimumWidth: screenScaleFactor * 600
    minimumHeight: screenScaleFactor * 800

    Rectangle  // Panel background
    {
        id: panelBackground
        anchors.fill: parent
        radius: UM.Theme.getSize("default_radius").width
        color: UM.Theme.getColor("main_background")

        UM.ProgressBar
        {
            id: progressBar
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right

            height: UM.Theme.getSize("progressbar").height

            value: base.progressValue
        }

        Loader
        {
            id: contentLoader
            anchors
            {
                margins: UM.Theme.getSize("wide_margin").width
                bottomMargin: UM.Theme.getSize("default_margin").width
                top: progressBar.bottom
                bottom: parent.bottom
                left: parent.left
                right: parent.right
            }
            source: base.pageUrl
        }


    Column  // Arrange the items vertically and put everything in the center
    {
        anchors.centerIn: parent
        width: parent.width
        spacing: 2 * UM.Theme.getSize("wide_margin").height

        Label
        {
            id: titleLabel
            anchors.horizontalCenter: parent.horizontalCenter
            horizontalAlignment: Text.AlignHCenter
            text: catalog.i18nc("@label", "Welcome to the Hydra Research Plugin")
            color: UM.Theme.getColor("primary_button")
            font: UM.Theme.getFont("huge")
            renderType: Text.NativeRendering
        }

        Image
        {
            id: curaImage
            anchors.horizontalCenter: parent.horizontalCenter
            source: "../img/logo.png"
        }

        Label
        {
            id: textLabel
            anchors.horizontalCenter: parent.horizontalCenter
            horizontalAlignment: Text.AlignHCenter
            text: catalog.i18nc("@text", "Please follow these steps to set up\nCura for your Hydra Research printer")
            font: UM.Theme.getFont("medium")
            color: UM.Theme.getColor("text")
            renderType: Text.NativeRendering
        }

        //Cura.PrimaryButton
        //{
          //  id: getStartedButton
            //anchors.horizontalCenter: parent.horizontalCenter
            //anchors.margins: UM.Theme.getSize("wide_margin").width
            //text: catalog.i18nc("@button", "Get started")
            //onClicked: base.showNextPage()
        //}
    }
}
}
