// Copyright (c) 2019 Ultimaker B.V.
// Cura is released under the terms of the LGPLv3 or higher.

import QtQuick 2.10
import QtQuick.Controls 2.3

import UM 1.3 as UM
import Cura 1.1 as Cura


//
// This component contains the content for to add a Nautilus in the welcome flow
//
Item
{
    UM.I18nCatalog { id: catalog; name: "cura" }

    Label
    {
        id: titleLabel
        anchors.top: parent.top
        anchors.horizontalCenter: parent.horizontalCenter
        horizontalAlignment: Text.AlignHCenter
        text: catalog.i18nc("@label", "Add a Nautilus")
        color: UM.Theme.getColor("primary_button")
        font: UM.Theme.getFont("huge")
        renderType: Text.NativeRendering
    }

    // Area where the cloud contents can be put. Pictures, texts and such.
    Item
    {
        id: cloudContentsArea
        anchors
        {
            top: titleLabel.bottom
            bottom: finishButton.top
            left: parent.left
            right: parent.right
            topMargin: UM.Theme.getSize("default_margin").height
        }

        // Pictures and texts are arranged using Columns with spacing. The whole picture and text area is centered in
        // the cloud contents area.
        Column
        {
            anchors.centerIn: parent
            width: parent.width
            height: childrenRect.height

            spacing: 20 * screenScaleFactor

            Image  // Cloud image
            {
                id: cloudImage
                anchors.horizontalCenter: parent.horizontalCenter
                source: "../../img/nautilus.png"
            }

            Label  // A title-ish text
            {
                id: highlightTextLabel
                anchors.horizontalCenter: parent.horizontalCenter
                horizontalAlignment: Text.AlignHCenter
                text: catalog.i18nc("@text", "Add your Nautilus")
                textFormat: Text.RichText
                color: UM.Theme.getColor("primary")
                font: UM.Theme.getFont("medium")
                renderType: Text.NativeRendering
            }

            Label  // A number of text items
            {
                id: textLabel
                anchors.horizontalCenter: parent.horizontalCenter
                text:
                {
                    // There are 3 text items, each of which is translated separately as a single piece of text.
                    var full_text = ""
                    var t = ""

                    t = catalog.i18nc("@text", "- Send print jobs wirelessly to your Hydra Research printer")
                    full_text += "<p>" + t + "</p>"

                    t = catalog.i18nc("@text", "- Monitor and control your Nautilus from the web interface")
                    full_text += "<p>" + t + "</p>"

                    t = catalog.i18nc("@text", "- Get highly tuned profiles specifically for your printer")
                    full_text += "<p>" + t + "</p>"

                    return full_text
                }
                textFormat: Text.RichText
                font: UM.Theme.getFont("medium")
                color: UM.Theme.getColor("text")
                renderType: Text.NativeRendering
            }
        }
    }

    // Bottom buttons go here
    Cura.PrimaryButton
    {
        id: finishButton
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        text: catalog.i18nc("@button", "Next")
        onClicked: base.showNextPage()
    }

    Cura.SecondaryButton
    {
        id: createAccountButton
        anchors.left: parent.left
        anchors.verticalCenter: finishButton.verticalCenter
        text: catalog.i18nc("@button", "Add a Nautilus")
        onClicked: manager.addNautilus()
    }
}
