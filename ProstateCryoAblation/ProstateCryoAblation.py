import ast
import os
import logging
import qt
import vtk

from ProstateCryoAblationUtils.appConfig import ConfigurationParser
from ProstateCryoAblationUtils.session import ProstateCryoAblationSession
from ProstateCryoAblationUtils.steps.base import ProstateCryoAblationStep
from ProstateCryoAblationUtils.steps.overview import ProstateCryoAblationOverviewStep
from ProstateCryoAblationUtils.steps.zFrameRegistration import ProstateCryoAblationZFrameRegistrationStep
from ProstateCryoAblationUtils.steps.intraOperativeTargeting import ProstateCryoAblationTargetingStep
from ProstateCryoAblationUtils.steps.intraOperativeGuidance import ProstateCryoAblationGuidanceStep
from ProstateCryoAblationUtils.steps.plugins.buttons import ScreenShotButton
from SlicerDevelopmentToolboxUtils.buttons import *
from SlicerDevelopmentToolboxUtils.events import SlicerDevelopmentToolboxEvents
from SlicerDevelopmentToolboxUtils.constants import DICOMTAGS
from SlicerDevelopmentToolboxUtils.decorators import logmethod
from SlicerDevelopmentToolboxUtils.helpers import WatchBoxAttribute
from SlicerDevelopmentToolboxUtils.mixins import ModuleWidgetMixin, ModuleLogicMixin
from SlicerDevelopmentToolboxUtils.widgets import CustomStatusProgressbar, DICOMBasedInformationWatchBox
from slicer.ScriptedLoadableModule import *
from SlicerDevelopmentToolboxUtils.icons import Icons

class ProstateCryoAblation(ScriptedLoadableModule):

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "ProstateCryoAblation"
    self.parent.categories = ["IGT"]
    self.parent.dependencies = ["SlicerDevelopmentToolbox"]
    self.parent.contributors = ["Longquan Chen(SPL)", "Christian Herz(SPL)", "Junichi Tokuda (SPL)"]
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

    for step in [ProstateCryoAblationOverviewStep, ProstateCryoAblationZFrameRegistrationStep, ProstateCryoAblationTargetingStep, ProstateCryoAblationGuidanceStep]:
      registeredStep = step(self.session)
      self.session.registerStep(registeredStep)
    
    self.customStatusProgressBar = CustomStatusProgressbar()
    self.setupPatientWatchBox()
    self.setupViewSettingGroupBox()
    self.setupTabBarNavigation()
    self.setupSessionObservers()

  def setupPatientWatchBox(self):
    WatchBoxAttribute.TRUNCATE_LENGTH = 20
    self.patientWatchBoxInformation = [WatchBoxAttribute('PatientName', 'Name: ', DICOMTAGS.PATIENT_NAME, masked=self.demoMode),
                                       WatchBoxAttribute('PatientID', 'PID: ', DICOMTAGS.PATIENT_ID, masked=self.demoMode),
                                       WatchBoxAttribute('DOB', 'DOB: ', DICOMTAGS.PATIENT_BIRTH_DATE, masked=self.demoMode),
                                       WatchBoxAttribute('StudyDate', 'StudyDate: ', DICOMTAGS.STUDY_DATE)]
    self.patientWatchBox = DICOMBasedInformationWatchBox(self.patientWatchBoxInformation, title="Patient Information",
                                                         columns=2)
    self.layout.addWidget(self.patientWatchBox)

    intraopWatchBoxInformation = [WatchBoxAttribute('CurrentSeries', 'Current Series: ', [DICOMTAGS.SERIES_NUMBER,
                                                                                          DICOMTAGS.SERIES_DESCRIPTION]),
                                  WatchBoxAttribute('StudyDate', 'Intraop Date: ', DICOMTAGS.STUDY_DATE)]
    self.intraopWatchBox = DICOMBasedInformationWatchBox(intraopWatchBoxInformation, columns=2)
    self.layout.addWidget(self.intraopWatchBox)

  def setupViewSettingGroupBox(self):
    iconSize = qt.QSize(24, 24)
    self.redOnlyLayoutButton = RedSliceLayoutButton()
    self.sideBySideLayoutButton = SideBySideLayoutButton()
    self.fourUpLayoutButton = FourUpLayoutButton()
    self.layoutButtons = [self.redOnlyLayoutButton, self.sideBySideLayoutButton, self.fourUpLayoutButton]

    self.screenShotButton = ScreenShotButton()
    self.screenShotButton.caseResultDir = ""
    self.settingsButton = ModuleSettingsButton(self.moduleName)
    self.affectiveZoneIcon = self.createIcon('icon-needle.png')
    self.showAffectiveZoneButton = self.createButton("", icon=self.affectiveZoneIcon, iconSize=iconSize, checkable=True, toolTip="Display the effective ablation zone")
    self.showAffectiveZoneButton.connect('toggled(bool)', self.session.onShowAffectiveZoneToggled)
    viewSettingButtons = [self.redOnlyLayoutButton, self.fourUpLayoutButton,
                          self.settingsButton, self.screenShotButton, self.showAffectiveZoneButton]
    
    for step in self.session.steps:
      viewSettingButtons += step.viewSettingButtons
      
    self.layout.addWidget(self.createHLayout(viewSettingButtons))
    self.setupAdditionalViewSettingButtons()
    self.resetViewSettingButtons()
  
  def setupAdditionalViewSettingButtons(self):
    for step in self.session.steps:
      step.setupIcons()
      step.setupAdditionalViewSettingButtons()
  
  def resetViewSettingButtons(self):
    for step in self.session.steps:
      step.resetViewSettingButtons()
    #self.crosshairButton.checked = False

  def setupTabBarNavigation(self):
    self.tabWidget = ProstateCryoAblationTabWidget(self.session)
    self.tabWidget.addEventObserver(self.tabWidget.AvailableLayoutsChangedEvent, self.onAvailableLayoutsChanged)
    self.layout.addWidget(self.tabWidget)
    self.tabWidget.hideTabs()
    
  def setupSessionObservers(self):
    self.session.addEventObserver(self.session.CurrentSeriesChangedEvent, self.onCurrentSeriesChanged)
    self.session.addEventObserver(self.session.NewCaseStartedEvent, self.onUpdateScreenShotDir)
    self.session.addEventObserver(self.session.CaseOpenedEvent, self.onUpdateScreenShotDir)

  def removeSessionObservers(self):
    self.session.removeEventObserver(self.session.CurrentSeriesChangedEvent, self.onCurrentSeriesChanged)
    self.session.removeEventObserver(self.session.NewCaseStartedEvent, self.onUpdateScreenShotDir)
    self.session.removeEventObserver(self.session.CaseOpenedEvent, self.onUpdateScreenShotDir)

  def onUpdateScreenShotDir(self, caller, event):
    self.screenShotButton.caseResultDir = self.session.outputDirectory

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
    if self.patientWatchBox.sourceFile is None:
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


class ProstateCryoAblationTabWidget(qt.QTabWidget, ModuleWidgetMixin):

  AvailableLayoutsChangedEvent = ProstateCryoAblationStep.AvailableLayoutsChangedEvent

  def __init__(self, prostateCryoAblationSession):
    super(ProstateCryoAblationTabWidget, self).__init__()
    self.session = prostateCryoAblationSession
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
    self.updateSizes(index)

  def updateSizes(self, index):
    for i in range(self.count):
      if i != index:
        self.widget(i).setSizePolicy(qt.QSizePolicy.Ignored, qt.QSizePolicy.Ignored)

    self.widget(index).setSizePolicy(qt.QSizePolicy.Preferred, qt.QSizePolicy.Preferred)
    self.widget(index).resize(self.widget(index).minimumSizeHint)
    self.resize(self.minimumSizeHint)
    self.adjustSize()


class ProstateCryoAblationSlicelet(qt.QWidget, ModuleWidgetMixin):

  class MainWindow(qt.QWidget):

    def __init__(self, parent=None):
      qt.QWidget.__init__(self)
      self.objectName = "qSlicerAppMainWindow"
      self.setLayout(qt.QVBoxLayout())
      self.mainFrame = qt.QFrame()
      self.mainFrame.setLayout(qt.QHBoxLayout())

      self._statusBar = qt.QStatusBar()
      self._statusBar.setMaximumHeight(35)

      self.layout().addWidget(self.mainFrame)
      self.layout().addWidget(self._statusBar)

    def statusBar(self):
      self._statusBar = getattr(self, "_statusBar", None)
      if not self._statusBar:
        self._statusBar = qt.QStatusBar()
      return self._statusBar

  def __init__(self):
    qt.QWidget.__init__(self)

    print slicer.dicomDatabase

    self.mainWidget = ProstateCryoAblationSlicelet.MainWindow()

    self.setupLayoutWidget()

    self.moduleFrame = qt.QWidget()
    self.moduleFrame.setLayout(qt.QVBoxLayout())
    self.widget = ProstateCryoAblationWidget(self.moduleFrame)
    self.widget.setup()

    # TODO: resize self.widget.parent to minimum possible width

    self.scrollArea = qt.QScrollArea()
    self.scrollArea.setWidget(self.widget.parent)
    self.scrollArea.setWidgetResizable(True)
    self.scrollArea.setMinimumWidth(self.widget.parent.minimumSizeHint.width())

    self.splitter = qt.QSplitter()
    self.splitter.setOrientation(qt.Qt.Horizontal)
    self.splitter.addWidget(self.scrollArea)
    self.splitter.addWidget(self.layoutWidget)
    self.splitter.splitterMoved.connect(self.onSplitterMoved)

    self.splitter.setStretchFactor(0,0)
    self.splitter.setStretchFactor(1,1)
    self.splitter.handle(1).installEventFilter(self)

    self.mainWidget.mainFrame.layout().addWidget(self.splitter)
    self.mainWidget.show()

  def setupLayoutWidget(self):
    self.layoutWidget = qt.QWidget()
    self.layoutWidget.setLayout(qt.QHBoxLayout())
    layoutWidget = slicer.qMRMLLayoutWidget()
    layoutManager = slicer.qSlicerLayoutManager()
    layoutManager.setMRMLScene(slicer.mrmlScene)
    layoutManager.setScriptedDisplayableManagerDirectory(slicer.app.slicerHome + "/bin/Python/mrmlDisplayableManager")
    layoutWidget.setLayoutManager(layoutManager)
    slicer.app.setLayoutManager(layoutManager)
    layoutWidget.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    self.layoutWidget.layout().addWidget(layoutWidget)

  def eventFilter(self, obj, event):
    if event.type() == qt.QEvent.MouseButtonDblClick:
      self.onSplitterClick()

  def onSplitterMoved(self, pos, index):
    vScroll = self.scrollArea.verticalScrollBar()
    print self.moduleFrame.width, self.widget.parent.width, self.scrollArea.width, vScroll.width
    vScrollbarWidth = 4 if not vScroll.isVisible() else vScroll.width + 4 # TODO: find out, what is 4px wide
    if self.scrollArea.minimumWidth != self.widget.parent.minimumSizeHint.width() + vScrollbarWidth:
      self.scrollArea.setMinimumWidth(self.widget.parent.minimumSizeHint.width() + vScrollbarWidth)

  def onSplitterClick(self):
    if self.splitter.sizes()[0] > 0:
      self.splitter.setSizes([0, self.splitter.sizes()[1]])
    else:
      minimumWidth = self.widget.parent.minimumSizeHint.width()
      self.splitter.setSizes([minimumWidth, self.splitter.sizes()[1]-minimumWidth])


if __name__ == "ProstateCryoAblationSlicelet":
  import sys
  print( sys.argv )

  slicelet = ProstateCryoAblationSlicelet()    
