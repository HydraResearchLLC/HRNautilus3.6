import QtQuick 2.7
import QtQuick.Controls 1.4
import QtQuick.Controls.Styles 1.4
import QtQuick.Layouts 1.1
import QtQuick.Dialogs 1.2
import QtGraphicalEffects 1.0

import UM 1.3 as UM
import Cura 1.1 as Cura

UM.Dialog{
  minimumWidth: screenScaleFactor * 580
  minimumHeight: screenScaleFactor * 600
WelcomeDialogItem
{
    id: welcomeDialogItem
    visible: true  // True, so if somehow no preferences are found/loaded, it's shown anyway.
  //  z: greyOutBackground.z + 1
}

}
