import ast
import os
import logging
import qt
import vtk

from ProstateCryoAblationUtil.appConfig import ConfigurationParser
from ProstateCryoAblationUtil.constants import ProstateCryoAblationConstants
from SliceTracker import SliceTrackerTabWidget
from SliceTrackerUtils.session import SliceTrackerSession
from SliceTrackerUtils.steps.base import SliceTrackerStep
from SliceTrackerUtils.steps.overview import SliceTrackerOverviewStep
from SliceTrackerUtils.steps.zFrameRegistration import SliceTrackerZFrameRegistrationStep
from ProstateCryoAblationUtil.steps.intraOperativeTargeting import ProstateCryoAblationTargetingStep

from SlicerDevelopmentToolboxUtils.buttons import *
from SlicerDevelopmentToolboxUtils.constants import DICOMTAGS
from SlicerDevelopmentToolboxUtils.decorators import logmethod
from SlicerDevelopmentToolboxUtils.helpers import WatchBoxAttribute
from SlicerDevelopmentToolboxUtils.mixins import ModuleWidgetMixin, ModuleLogicMixin
from SlicerDevelopmentToolboxUtils.widgets import CustomStatusProgressbar, DICOMBasedInformationWatchBox
from slicer.ScriptedLoadableModule import *


class ProstateCryoAblation(ScriptedLoadableModule):

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "ProstateCryoAblation"
    self.parent.categories = ["IGT"]
    self.parent.dependencies = ["SlicerProstate", "SliceTracker", "SlicerDevelopmentToolbox"]
    self.parent.contributors = ["Longquan Chen(SPL)", "Junichi Tokuda (SPL)"]
    self.parent.helpText = """ module to support MRI-guided prostate cryoablation.
      See <a href=\"https://www.slicer.org/wiki/Modules:ProstateNav-Documentation-3.6\"> """
    self.parent.acknowledgementText = """Surgical Planning Laboratory, Brigham and Women's Hospital, Harvard
                                          Medical School, Boston, USA This work was supported in part by the National
                                          Institutes of Health through grants xxx, xxx."""


class ProstateCryoAblationWidget(ModuleWidgetMixin, ScriptedLoadableModuleWidget):

  def __init__(self, parent=None):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    self.modulePath = os.path.dirname(slicer.util.modulePath(self.moduleName))
    ConfigurationParser(os.path.join(self.modulePath, 'Resources', "default.cfg"))
    self.logic = ProstateCryoAblationLogic()

    self.session = SliceTrackerSession()
    self.session.steps = []
    self.session.removeEventObservers()
    self.session.addEventObserver(self.session.CloseCaseEvent, lambda caller, event: self.cleanup())
    self.session.addEventObserver(SlicerDevelopmentToolboxEvents.NewFileIndexedEvent, self.onNewFileIndexed)
    self.demoMode = False

  def enter(self):
    if not slicer.dicomDatabase:
      slicer.util.errorDisplay("Slicer DICOMDatabase was not found. In order to be able to use SliceTracker, you will "
                               "need to set a proper location for the Slicer DICOMDatabase.")
    self.layout.parent().enabled = slicer.dicomDatabase is not None

  def exit(self):
    pass

  def onReload(self):
    ScriptedLoadableModuleWidget.onReload(self)

  @logmethod(logging.DEBUG)
  def cleanup(self):
    ScriptedLoadableModuleWidget.cleanup(self)
    self.patientWatchBox.sourceFile = None
    self.intraopWatchBox.sourceFile = None

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    for step in [SliceTrackerOverviewStep, SliceTrackerZFrameRegistrationStep,
                 ProstateCryoAblationTargetingStep]:
      self.session.registerStep(step())

    self.customStatusProgressBar = CustomStatusProgressbar()
    self.setupIcons()
    self.setupPatientWatchBox()
    self.setupViewSettingGroupBox()
    self.setupTabBarNavigation()
    self.setupConnections()
    self.setupSessionObservers()
    self.layout.addStretch(1)

  def setupIcons(self):
    self.settingsIcon = self.createIcon('icon-settings.png')
    self.textInfoIcon = self.createIcon('icon-text-info.png')

  def setupPatientWatchBox(self):
    WatchBoxAttribute.TRUNCATE_LENGTH = 20
    self.patientWatchBoxInformation = [WatchBoxAttribute('PatientName', 'Name: ', DICOMTAGS.PATIENT_NAME, masked=self.demoMode),
                                       WatchBoxAttribute('PatientID', 'PID: ', DICOMTAGS.PATIENT_ID, masked=self.demoMode),
                                       WatchBoxAttribute('DOB', 'DOB: ', DICOMTAGS.PATIENT_BIRTH_DATE, masked=self.demoMode),
                                       WatchBoxAttribute('StudyDate', 'Preop Date: ', DICOMTAGS.STUDY_DATE)]
    self.patientWatchBox = DICOMBasedInformationWatchBox(self.patientWatchBoxInformation, title="Patient Information",
                                                         columns=2)
    self.layout.addWidget(self.patientWatchBox)

    intraopWatchBoxInformation = [WatchBoxAttribute('CurrentSeries', 'Current Series: ', [DICOMTAGS.SERIES_NUMBER,
                                                                                          DICOMTAGS.SERIES_DESCRIPTION]),
                                  WatchBoxAttribute('StudyDate', 'Intraop Date: ', DICOMTAGS.STUDY_DATE)]
    self.intraopWatchBox = DICOMBasedInformationWatchBox(intraopWatchBoxInformation, columns=2)
    self.registrationDetailsButton = self.createButton("", icon=self.settingsIcon, styleSheet="border:none;",
                                                       maximumWidth=16)
    self.layout.addWidget(self.intraopWatchBox)

  def setupViewSettingGroupBox(self):
    iconSize = qt.QSize(24, 24)
    self.redOnlyLayoutButton = RedSliceLayoutButton()
    self.sideBySideLayoutButton = SideBySideLayoutButton()
    self.fourUpLayoutButton = FourUpLayoutButton()
    self.layoutButtons = [self.redOnlyLayoutButton, self.sideBySideLayoutButton, self.fourUpLayoutButton]
    self.crosshairButton = CrosshairButton()
    self.wlEffectsToolButton = WindowLevelEffectsButton()
    self.settingsButton = ModuleSettingsButton(self.moduleName)
    self.showAnnotationsButton = self.createButton("", icon=self.textInfoIcon, iconSize=iconSize, checkable=True, toolTip="Display annotations", checked=True)

    viewSettingButtons = [self.redOnlyLayoutButton, self.sideBySideLayoutButton, self.fourUpLayoutButton,
                          self.crosshairButton,   self.wlEffectsToolButton, self.settingsButton]

    for step in self.session.steps:
      viewSettingButtons += step.viewSettingButtons

    self.layout.addWidget(self.createHLayout(viewSettingButtons))

    self.resetViewSettingButtons()

  def resetViewSettingButtons(self):
    for step in self.session.steps:
      step.resetViewSettingButtons()
    self.wlEffectsToolButton.checked = False
    self.crosshairButton.checked = False

  def setupTabBarNavigation(self):
    self.tabWidget = SliceTrackerTabWidget()
    self.tabWidget.addEventObserver(self.tabWidget.AvailableLayoutsChangedEvent, self.onAvailableLayoutsChanged)
    self.layout.addWidget(self.tabWidget)
    self.tabWidget.hideTabs()

  def setupConnections(self):
    self.showAnnotationsButton.connect('toggled(bool)', self.onShowAnnotationsToggled)

  def setupSessionObservers(self):
    self.session.addEventObserver(self.session.PreprocessingSuccessfulEvent, self.onSuccessfulPreProcessing)
    self.session.addEventObserver(self.session.CurrentSeriesChangedEvent, self.onCurrentSeriesChanged)

  def removeSessionObservers(self):
    self.session.removeEventObserver(self.session.PreprocessingSuccessfulEvent, self.onSuccessfulPreProcessing)
    self.session.removeEventObserver(self.session.CurrentSeriesChangedEvent, self.onCurrentSeriesChanged)

  def onSuccessfulPreProcessing(self, caller, event):
    dicomFileName = self.logic.getFileList(self.session.preopDICOMDirectory)[0]
    self.patientWatchBox.sourceFile = os.path.join(self.session.preopDICOMDirectory, dicomFileName)

  def onShowAnnotationsToggled(self, checked):
    allSliceAnnotations = self.sliceAnnotations[:]

  @vtk.calldata_type(vtk.VTK_STRING)
  def onNewFileIndexed(self, caller, event, callData):
    text, size, currentIndex = ast.literal_eval(callData)
    if not self.customStatusProgressBar.visible:
      self.customStatusProgressBar.show()
    self.customStatusProgressBar.maximum = size
    self.customStatusProgressBar.updateStatus(text, currentIndex)

  @vtk.calldata_type(vtk.VTK_STRING)
  def onCurrentSeriesChanged(self, caller, event, callData):
    receivedFile = self.session.loadableList[callData][0] if callData else None
    if not self.session.data.usePreopData and self.patientWatchBox.sourceFile is None:
      self.patientWatchBox.sourceFile = receivedFile
    self.intraopWatchBox.sourceFile = receivedFile

  @vtk.calldata_type(vtk.VTK_STRING)
  def onAvailableLayoutsChanged(self, caller, event, callData):
    layouts = ast.literal_eval(callData)
    for layoutButton in self.layoutButtons:
      layoutButton.enabled = layoutButton.LAYOUT in layouts

class ProstateCryoAblationLogic(ModuleLogicMixin):
  def __init__(self):
    pass
