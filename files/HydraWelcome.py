"HRpage_url"# Copyright (c) 2019 Ultimaker B.V.
# Cura is released under the terms of the LGPLv3 or higher.
from collections import deque
import os
from typing import TYPE_CHECKING, Optional, List, Dict, Any

from PyQt5.QtCore import QUrl, Qt, pyqtSlot, pyqtProperty, pyqtSignal

from UM.i18n import i18nCatalog
from UM.Logger import Logger
from UM.Qt.ListModel import ListModel
from UM.Resources import Resources
from UM.PluginRegistry import PluginRegistry

if TYPE_CHECKING:
    from PyQt5.QtCore import QObject
    from cura.CuraApplication import CuraApplication


#
# This is the Qt ListModel that contains all welcome pages data. Each page is a page that can be shown as a step in the
# welcome wizard dialog. Each item in this ListModel represents a page, which contains the following fields:
#
#  - id           : A unique page_id which can be used in function goToPage(page_id)
#  - page_url     : The QUrl to the QML file that contains the content of this page
#  - next_page_id : (OPTIONAL) The next page ID to go to when this page finished. This is optional. If this is not
#                   provided, it will go to the page with the crnt index + 1
#  - next_page_button_text: (OPTIONAL) The text to show for the "next" button, by default it's the translated text of
#                           "Next". Note that each step QML can decide whether to use this text or not, so it's not
#                           mandatory.
#  - should_show_function : (OPTIONAL) An optional function that returns True/False indicating if this page should be
#                           shown. By default all pages should be shown. If a function returns False, that page will
#                           be skipped and its next page will be shown.
#
# Note that in any case, a page that has its "should_show_function" == False will ALWAYS be skipped.
#
class HydraWelcome(ListModel):

    IdHRRole = Qt.UserRole + 1  # Page ID
    PageUrlHRRole = Qt.UserRole + 2  # URL to the page's QML file
    NextPageIdHRRole = Qt.UserRole + 3  # The next page ID it should go to
    NextPageButtonTextHRRole = Qt.UserRole + 4  # The text for the next page button
    PreviousPageButtonTextHRRole = Qt.UserRole + 5  # The text for the previous page button

    def __init__(self, application: "CuraApplication", parent: Optional["QObject"] = None) -> None:
        super().__init__(parent)

        self.addRoleName(self.IdHRRole, "HRid")
        self.addRoleName(self.PageUrlHRRole, "HRpage_url")
        self.addRoleName(self.NextPageIdHRRole, "HRnext_page_id")
        self.addRoleName(self.NextPageButtonTextHRRole, "HRnext_page_button_text")
        self.addRoleName(self.PreviousPageButtonTextHRRole, "HRprevious_page_button_text")

        self._application = application
        self._catalog = i18nCatalog("cura")

        self._default_next_button_text = self._catalog.i18nc("@action:button", "Next")

        self._pages = []  # type: List[Dict[str, Any]]

        self._crnt_page_index = 0
        # Store all the previous page indices so it can go back.
        self._previous_page_indices_stack = deque()  # type: deque

        # If the welcome flow should be shown. It can show the complete flow or just the changelog depending on the
        # specific case. See initialize() for how this variable is set.
        self._should_show_welcome_flow = False

    allFinished = pyqtSignal()  # emitted when all steps have been finished
    CrntPgIndexChange = pyqtSignal()

    @pyqtProperty(int, notify = CrntPgIndexChange)
    def crntPageIndex(self) -> int:
        Logger.log("i","crntpageindex"+str(self._crnt_page_index))
        return self._crnt_page_index

    @pyqtSlot(result=str)
    def ChangelogText(self) -> str:
        Logger.log("i","Acquring changelog")
        this_path = os.path.join(Resources.getStoragePath(Resources.Resources), "plugins","Nautilus","Nautilus")
        changes = open(os.path.join(this_path,"Changelog.txt"),'r').read()
        Logger.log("i","Going through changes "+str(type(changes)))
        return changes

    # Returns a float number in [0, 1] which indicates the crnt progress.
    @pyqtProperty(float, notify = CrntPgIndexChange)
    def crntProgress(self) -> float:
        Logger.log("i","crntprogress")
        if len(self._items) == 0:
            Logger.log("i","crntprogress returning 0")
            return 0
        else:
            Logger.log("i","crntprogress returning "+str(self._crnt_page_index)+" "+str(len(self._items)))
            return self._crnt_page_index / len(self._items)

    # Indicates if the crnt page is the last page.
    @pyqtProperty(bool, notify = CrntPgIndexChange)
    def isCrntPageLast(self) -> bool:
        Logger.log("i","iscrntpagelast")
        return self._crnt_page_index == len(self._items) - 1

    def _setCrntPageIndex(self, page_index: int) -> None:
        Logger.log("i","_setCrntPageIndex")
        if page_index != self._crnt_page_index:
            self._previous_page_indices_stack.append(self._crnt_page_index)
            self._crnt_page_index = page_index
            self.CrntPgIndexChange.emit()

    # Ends the Welcome-Pages. Put as a separate function for cases like the 'decline' in the User-Agreement.
    @pyqtSlot()
    def atEnd(self) -> None:
        Logger.log("i","atend")
        self.allFinished.emit()
        #self._welcome_window.hide()
        self.resetState()

    # Goes to the next page.
    # If "from_index" is given, it will look for the next page to show starting from the "from_index" page instead of
    # the "self._crnt_page_index".
    @pyqtSlot()
    def goToNextPage(self, from_index: Optional[int] = None) -> None:
        Logger.log("i","goTonextPage")
        # Look for the next page that should be shown
        crnt_index = self._crnt_page_index if from_index is None else from_index
        while True:
            page_item = self._items[crnt_index]

            # Check if there's a "next_page_id" assigned. If so, go to that page. Otherwise, go to the page with the
            # crnt index + 1.
            next_page_id = page_item.get("HRnext_page_id")
            next_page_index = crnt_index + 1
            if next_page_id:
                idx = self.getPageIndexById(next_page_id)
                if idx is None:
                    # FIXME: If we cannot find the next page, we cannot do anything here.
                    Logger.log("e", "Cannot find page with ID [%s]", next_page_id)
                    return
                next_page_index = idx

            # If we have reached the last page, emit allFinished signal and reset.
            if next_page_index == len(self._items):
                self.atEnd()
                return

            # Check if the this page should be shown (default yes), if not, keep looking for the next one.
            next_page_item = self.getItem(next_page_index)
            if self._shouldPageBeShown(next_page_index):
                break

            Logger.log("d", "Page [%s] should not be displayed, look for the next page.", next_page_item["HRid"])
            crnt_index = next_page_index

        # Move to the next page
        self._setCrntPageIndex(next_page_index)

    # Goes to the previous page. If there's no previous page, do nothing.
    @pyqtSlot()
    def goToPreviousPage(self) -> None:
        Logger.log("i","previouspage")
        if len(self._previous_page_indices_stack) == 0:
            Logger.log("i", "No previous page, do nothing")
            return

        previous_page_index = self._previous_page_indices_stack.pop()
        self._crnt_page_index = previous_page_index
        self.CrntPgIndexChange.emit()

    # Sets the crnt page to the given page ID. If the page ID is not found, do nothing.
    @pyqtSlot(str)
    def goToPage(self, page_id: str) -> None:
        Logger.log("i","gotopage")
        page_index = self.getPageIndexById(page_id)
        if page_index is None:
            # FIXME: If we cannot find the next page, we cannot do anything here.
            Logger.log("e", "Cannot find page with ID [%s], go to the next page by default", page_index)
            self.goToNextPage()
            return

        if self._shouldPageBeShown(page_index):
            # Move to that page if it should be shown
            self._setCrntPageIndex(page_index)
        else:
            # Find the next page to show starting from the "page_index"
            self.goToNextPage(from_index = page_index)

    # Checks if the page with the given index should be shown by calling the "should_show_function" associated with it.
    # If the function is not present, returns True (show page by default).
    def _shouldPageBeShown(self, page_index: int) -> bool:
        Logger.log("i","_shouldPageBeShown")
        next_page_item = self.getItem(page_index)
        should_show_function = next_page_item.get("should_show_function", lambda: True)
        return should_show_function()

    # Resets the state of the WelcomePagesModel. This functions does the following:
    #  - Resets crnt_page_index to 0
    #  - Clears the previous page indices stack
    @pyqtSlot()
    def resetState(self) -> None:
        Logger.log("i","resetstate")
        self._crnt_page_index = 0
        self._previous_page_indices_stack.clear()

        self.CrntPgIndexChange.emit()
        self._welcome_window.hide()

    shouldShowWelcomeFlowChanged = pyqtSignal()

    @pyqtProperty(bool, notify = shouldShowWelcomeFlowChanged)
    def shouldShowWelcomeFlow(self) -> bool:
        Logger.log("i","shouldShowWelcomeFlow")
        return self._should_show_welcome_flow

    # Gets the page index with the given page ID. If the page ID doesn't exist, returns None.
    def getPageIndexById(self, page_id: str) -> Optional[int]:
        Logger.log("i","getPageIndexById")
        page_idx = None
        for idx, page_item in enumerate(self._items):
            if page_item["HRid"] == page_id:
                page_idx = idx
                break
        return page_idx

    # Convenience function to get QUrl path to pages that's located in "resources/qml/WelcomePages".
    def _getBuiltinWelcomePagePath(self, page_filename: str) -> "QUrl":
        Logger.log("i","_getBuiltinWelcomePagePath")
        from cura.CuraApplication import CuraApplication

        return QUrl.fromLocalFile(os.path.join(Resources.getStoragePath(Resources.Resources), "plugins","Nautilus","Nautilus", "qml", "welcome", page_filename))

    def createWelcomeWindow(self):
        from cura.CuraApplication import CuraApplication
        path = os.path.join(Resources.getStoragePath(Resources.Resources), "plugins","Nautilus","Nautilus", "qml", "welcome", "Welcomer.qml")
        Logger.log("i","Creating Hydra welcome UI"+path)
        self._initialize()
        self._welcome_window = CuraApplication.getInstance().createQmlComponent(path, {"manager":self})
        self._welcome_window.show()

    # FIXME: HACKs for optimization that we don't update the model every time the active machine gets changed.
    def _onActiveMachineChanged(self) -> None:
        #self._application.getMachineManager().globalContainerChanged.disconnect(self._onActiveMachineChanged)
        self._initialize(update_should_show_flag = False)

    def initialize(self) -> None:
        Logger.log("i","initialize")
        #self._application.getMachineManager().globalContainerChanged.connect(self._onActiveMachineChanged)
        self._initialize()

    def _initialize(self, update_should_show_flag: bool = True) -> None:
        Logger.log("i","_initialize")
        """show_whatsnew_only = False
        if update_should_show_flag:
            has_active_machine = self._application.getMachineManager().activeMachine is not None
            has_app_just_upgraded = self._application.hasJustUpdatedFromOldVersion()

            # Only show the what's new dialog if there's no machine and we have just upgraded
            show_complete_flow = not has_active_machine
            show_whatsnew_only = has_active_machine and has_app_just_upgraded

            # FIXME: This is a hack. Because of the circular dependency between MachineManager, ExtruderManager, and
            # possibly some others, setting the initial active machine is not done when the MachineManager gets initialized.
            # So at this point, we don't know if there will be an active machine or not. It could be that the active machine
            # files are corrupted so we cannot rely on Preferences either. This makes sure that once the active machine
            # gets changed, this model updates the flags, so it can decide whether to show the welcome flow or not.
            should_show_welcome_flow = show_complete_flow or show_whatsnew_only
            if should_show_welcome_flow != self._should_show_welcome_flow:
                self._should_show_welcome_flow = should_show_welcome_flow
                self.shouldShowWelcomeFlowChanged.emit()"""
        should_show_welcome_flow = True
        self._should_show_welcome_flow = True
        # All pages
        all_pages_list = [{"HRid": "welcome",
                           "HRpage_url": self._getBuiltinWelcomePagePath("WelcomeContent.qml"),
                           },
                          {"HRid": "whats_new",
                           "HRpage_url": self._getBuiltinWelcomePagePath("WhatsNewContent.qml"),
                           },
                          {"HRid": "cloud",
                           "HRpage_url": self._getBuiltinWelcomePagePath("CloudContent.qml"),
                           },
                          ]

        pages_to_show = all_pages_list
        #if show_whatsnew_only:
        #    pages_to_show = list(filter(lambda x: x["id"] == "whats_new", all_pages_list))

        self._pages = pages_to_show
        self.setItems(self._pages)

    # For convenience, inject the default "next" button text to each item if it's not present.
    def setItems(self, items: List[Dict[str, Any]]) -> None:
        Logger.log("i","setItems"+str(len(items)))
        for item in items:
            if "HRnext_page_button_text" not in item:
                item["HRnext_page_button_text"] = self._default_next_button_text

        super().setItems(items)

    # Indicates if the machine action panel should be shown by checking if there's any first start machine actions
    # available.
    def shouldShowMachineActions(self) -> bool:
        Logger.log("i","shouldShowMachineActions")
        global_stack = self._application.getMachineManager().activeMachine
        if global_stack is None:
            return False

        definition_id = global_stack.definition.getId()
        first_start_actions = self._application.getMachineActionManager().getFirstStartActions(definition_id)
        return len([action for action in first_start_actions if action.needsUserInteraction()]) > 0

    def addPage(self) -> None:
        Logger.log("i","addPage")
        pass


__all__ = ["HydraWelcome"]
