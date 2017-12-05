import slicer
import os
import ctk
import vtk
import qt
import logging

from ...helpers import NewCaseSelectionNameWidget

from SlicerDevelopmentToolboxUtils.decorators import logmethod
from SlicerDevelopmentToolboxUtils.helpers import WatchBoxAttribute
from SlicerDevelopmentToolboxUtils.widgets import BasicInformationWatchBox

from ..base import ProstateCryoAblationPlugin, ProstateCryoAblationLogicBase
from SlicerDevelopmentToolboxUtils.icons import Icons

class ProstateCryoAblationCaseManagerLogic(ProstateCryoAblationLogicBase):

  def __init__(self, prostateCryoAblationSession):
    super(ProstateCryoAblationCaseManagerLogic, self).__init__(prostateCryoAblationSession)


class ProstateCryoAblationCaseManagerPlugin(ProstateCryoAblationPlugin):

  LogicClass = ProstateCryoAblationCaseManagerLogic
  NAME = "CaseManager"

  @property
  def caseRootDir(self):
    return self.casesRootDirectoryButton.directory

  @caseRootDir.setter
  def caseRootDir(self, path):
    try:
      exists = os.path.exists(path)
    except TypeError:
      exists = False
    self.setSetting('CasesRootLocation', path if exists else None)
    self.casesRootDirectoryButton.text = self.truncatePath(path) if exists else "Choose output directory"
    self.casesRootDirectoryButton.toolTip = path
    self.openCaseButton.enabled = exists
    self.createNewCaseButton.enabled = exists

  def __init__(self, prostateCryoAblationSession):
    super(ProstateCryoAblationCaseManagerPlugin, self).__init__(prostateCryoAblationSession)
    slicer.app.connect('aboutToQuit()', self.onSlicerQuits)

  def onSlicerQuits(self):
    if self.session.isRunning():
      self.onCloseCaseButtonClicked()

  def clearData(self):
    self.update()

  def setupIcons(self):
    self.newIcon = Icons.new
    self.openIcon = Icons.open
    self.closeIcon = Icons.exit

  def setup(self):
    self.setupIcons()
    iconSize = qt.QSize(36, 36)
    self.createNewCaseButton = self.createButton("", icon=self.newIcon, iconSize=iconSize, toolTip="Start a new case")
    self.openCaseButton = self.createButton("", icon=self.openIcon, iconSize=iconSize, toolTip="Open case")
    self.closeCaseButton = self.createButton("", icon=self.closeIcon, iconSize=iconSize,
                                             toolTip="Close case with resume support", enabled=False)
    self.setupCaseWatchBox()
    self.casesRootDirectoryButton = self.createDirectoryButton(text="Choose cases root location",
                                                               caption="Choose cases root location",
                                                               directory=self.getSetting('CasesRootLocation',
                                                                                         self.MODULE_NAME))
    self.caseRootDir = self.getSetting('CasesRootLocation', self.MODULE_NAME)
    self.caseDirectoryInformationArea = ctk.ctkCollapsibleButton()
    self.caseDirectoryInformationArea.collapsed = True
    self.caseDirectoryInformationArea.text = "Directory Settings"
    self.directoryConfigurationLayout = qt.QGridLayout(self.caseDirectoryInformationArea)
    self.directoryConfigurationLayout.addWidget(qt.QLabel("Cases Root Directory"), 1, 0, 1, 1)
    self.directoryConfigurationLayout.addWidget(self.casesRootDirectoryButton, 1, 1, 1, 1)
    self.directoryConfigurationLayout.addWidget(self.caseWatchBox, 2, 0, 1, qt.QSizePolicy.ExpandFlag)

    self.caseGroupBox = qt.QGroupBox("Case")
    self.caseGroupBoxLayout = qt.QFormLayout(self.caseGroupBox)
    self.caseGroupBoxLayout.addWidget(self.createHLayout([self.createNewCaseButton, self.openCaseButton,
                                                          self.closeCaseButton]))
    self.caseGroupBoxLayout.addWidget(self.caseDirectoryInformationArea)
    self.layout().addWidget(self.caseGroupBox)
    super(ProstateCryoAblationCaseManagerPlugin, self).setup()
    
  def setupCaseWatchBox(self):
    watchBoxInformation = [WatchBoxAttribute('CurrentCaseDirectory', 'Directory'),
                           WatchBoxAttribute('CurrentIntraopDICOMDirectory', 'Intraop DICOM Directory: ')
                           ]
    self.caseWatchBox = BasicInformationWatchBox(watchBoxInformation, title="Current Case")

  def setupConnections(self):
    self.createNewCaseButton.clicked.connect(self.onCreateNewCaseButtonClicked)
    self.openCaseButton.clicked.connect(self.onOpenCaseButtonClicked)
    self.closeCaseButton.clicked.connect(self.onCloseCaseButtonClicked)
    self.casesRootDirectoryButton.directoryChanged.connect(lambda: setattr(self, "caseRootDir",
                                                                           self.casesRootDirectoryButton.directory))

  def onCreateNewCaseButtonClicked(self):
    if not self.checkAndWarnUserIfCaseInProgress():
      return
    if self.session.isRunning():
      self.onCloseCaseButtonClicked()
    self.caseDialog = NewCaseSelectionNameWidget(self.caseRootDir)
    selectedButton = self.caseDialog.exec_()
    if selectedButton == qt.QMessageBox.Ok:
      self.session.createNewCase(self.caseDialog.newCaseDirectory)

  def onOpenCaseButtonClicked(self):
    if not self.checkAndWarnUserIfCaseInProgress():
      return
    if self.session.isRunning():
      self.onCloseCaseButtonClicked()
    self.session.directory = qt.QFileDialog.getExistingDirectory(self.parent().window(), "Select Case Directory",
                                                                 self.caseRootDir)

  def onCloseCaseButtonClicked(self):
    if self.session.data.completed:
      self.session.close(save=False)
    else:
      if slicer.util.confirmYesNoDisplay("Do you want to mark this case as completed? ", title="Complete Case",
                                         windowTitle="ProstateCryoAblation"):
        self.session.complete()
      else:
        self.session.close(save=slicer.util.confirmYesNoDisplay("Save the case data?", title="Close Case",
                                                                windowTitle="ProstateCryoAblation"))

  @logmethod(logging.INFO)
  def onNewCaseStarted(self, caller, event):
    self.update()

  @logmethod(logging.INFO)
  def onCaseOpened(self, caller, event):
    self.update()

  def update(self):
    self.updateCaseButtons()
    self.updateCaseWatchBox()

  @vtk.calldata_type(vtk.VTK_STRING)
  def onCaseClosed(self, caller, event, callData):
    self.clearData()

  def onLoadingMetadataSuccessful(self, caller, event):
    self.updateCaseButtons()

  def updateCaseWatchBox(self):
    if not self.session.isRunning():
      self.caseWatchBox.reset()
      return
    self.caseWatchBox.setInformation("CurrentCaseDirectory", os.path.relpath(self.session.directory, self.caseRootDir),
                                     toolTip=self.session.directory)
    self.caseWatchBox.setInformation("CurrentIntraopDICOMDirectory", os.path.relpath(self.session.intraopDICOMDirectory,
                                                                                     self.caseRootDir),
                                     toolTip=self.session.intraopDICOMDirectory)

  def updateCaseButtons(self):
    self.closeCaseButton.enabled = self.session.directory is not None

  def checkAndWarnUserIfCaseInProgress(self):
    if self.session.isRunning():
      if not slicer.util.confirmYesNoDisplay("Current case will be closed. Do you want to proceed?"):
        return False
    return True