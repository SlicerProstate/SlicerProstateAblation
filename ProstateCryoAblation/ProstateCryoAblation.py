import ast
import os
import logging
import qt
import vtk

from ProstateCryoAblationUtils.appConfig import ConfigurationParser
from ProstateCryoAblationUtils.constants import ProstateCryoAblationConstants
from ProstateCryoAblationUtils.steps.overview import ProstateCryoAblationOverviewStep
#from ProstateCryoAblation import ProstateCryoAblationTabWidget
from ProstateCryoAblationUtils.session import ProstateCryoAblationSession
from ProstateCryoAblationUtils.steps.base import ProstateCryoAblationStep
from ProstateCryoAblationUtils.steps.overview import ProstateCryoAblationOverviewStep
from ProstateCryoAblationUtils.steps.zFrameRegistration import ProstateCryoAblationZFrameRegistrationStep
from ProstateCryoAblationUtils.steps.intraOperativeTargeting import ProstateCryoAblationTargetingStep
#from ProstateCryoAblationUtils.steps.intraOperativeTargeting import ProstateCryoAblationTargetingStep

from SlicerDevelopmentToolboxUtils.buttons import *
from SlicerDevelopmentToolboxUtils.events import SlicerDevelopmentToolboxEvents
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
    self.parent.dependencies = ["SlicerProstate", "SlicerDevelopmentToolbox"]
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

    self.session = ProstateCryoAblationSession()
    self.session.steps = []
    self.session.removeEventObservers()
    self.session.addEventObserver(self.session.CloseCaseEvent, lambda caller, event: self.cleanup())
    self.session.addEventObserver(SlicerDevelopmentToolboxEvents.NewFileIndexedEvent, self.onNewFileIndexed)
    self.demoMode = False
    self.developerMode = True

  def enter(self):
    if not slicer.dicomDatabase:
      slicer.util.errorDisplay("Slicer DICOMDatabase was not found. In order to be able to use ProstateCryoAblation, you will "
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

    for step in [ProstateCryoAblationOverviewStep, ProstateCryoAblationZFrameRegistrationStep, ProstateCryoAblationTargetingStep]:
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
    viewSettingButtons = [self.redOnlyLayoutButton, self.fourUpLayoutButton,
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
    self.tabWidget = ProstateCryoAblationTabWidget()
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
    """
    backgroundVolumeID = self.session.getOrCreateVolumeForSeries(callData).GetID() if self.session.getOrCreateVolumeForSeries(
      callData) else None
    registrationResult = self.session.data.getApprovedOrLastResultForSeries(callData) if self.session.data.getResult(callData) else None
    if registrationResult:
      approvedVolume = registrationResult.volumes.asDict().get(registrationResult.registrationType)
      backgroundVolumeID = approvedVolume.GetID() if approvedVolume else None
    for widget in [w for w in self.getAllVisibleWidgets() if w.sliceView().visible]:
      compositeNode = widget.mrmlSliceCompositeNode()
      compositeNode.SetLabelVolumeID(None)
      compositeNode.SetForegroundVolumeID(None)
      compositeNode.SetBackgroundVolumeID(backgroundVolumeID)
    """

  @vtk.calldata_type(vtk.VTK_STRING)
  def onAvailableLayoutsChanged(self, caller, event, callData):
    layouts = ast.literal_eval(callData)
    for layoutButton in self.layoutButtons:
      layoutButton.enabled = layoutButton.LAYOUT in layouts

class ProstateCryoAblationLogic(ModuleLogicMixin):
  def __init__(self):
    pass


class ProstateCryoAblationTabWidget(qt.QTabWidget, ModuleWidgetMixin):

  AvailableLayoutsChangedEvent = ProstateCryoAblationStep.AvailableLayoutsChangedEvent

  def __init__(self):
    super(ProstateCryoAblationTabWidget, self).__init__()
    self.session = ProstateCryoAblationSession()
    self._createTabs()
    self.currentChanged.connect(self.onCurrentTabChanged)
    self.onCurrentTabChanged(0)

  def hideTabs(self):
    self.tabBar().hide()

  def _createTabs(self):
    for step in self.session.steps:
      logging.debug("Adding tab for %s step" % step.NAME)
      self.addTab(step, step.NAME)
      step.addEventObserver(step.ActivatedEvent, self.onStepActivated)
      step.addEventObserver(self.AvailableLayoutsChangedEvent, self.onStepAvailableLayoutChanged)

  @vtk.calldata_type(vtk.VTK_STRING)
  def onStepAvailableLayoutChanged(self, caller, event, callData):
    self.invokeEvent(self.AvailableLayoutsChangedEvent, callData)

  def onStepActivated(self, caller, event):
    name = caller.GetAttribute("Name")
    index = next((i for i, step in enumerate(self.session.steps) if step.NAME == name), None)
    if index is not None:
      self.setCurrentIndex(index)

  @logmethod(logging.DEBUG)
  def onCurrentTabChanged(self, index):
    for idx, step in enumerate(self.session.steps):
      if index != idx:
        if step.active:
          self.session.previousStep = step
        step.active = False
    self.session.steps[index].active = True
