import os
import ast
import qt
import slicer
import vtk
import SliceTracker
from ..UserEvents import ProstateCryoAblationUserEvents
from ..constants import ProstateCryoAblationConstants
from SliceTracker import SliceTrackerWidget
from SliceTrackerUtils.steps.base import SliceTrackerLogicBase, SliceTrackerStep
from SlicerDevelopmentToolboxUtils.helpers import SliceAnnotation
from SlicerDevelopmentToolboxUtils.decorators import onModuleSelected
from SliceTrackerUtils.steps.plugins.targeting import SliceTrackerTargetingPlugin


class ProstateCryoAblationTargetingStepLogic(SliceTrackerLogicBase):

  def __init__(self):
    super(ProstateCryoAblationTargetingStepLogic, self).__init__()


class ProstateCryoAblationTargetingStep(SliceTrackerStep):

  NAME = "Targeting"
  LogicClass = ProstateCryoAblationTargetingStepLogic

  def __init__(self):
    self.modulePath = os.path.dirname(slicer.util.modulePath(self.MODULE_NAME)).replace(".py", "")
    iconPathDir = os.path.dirname(slicer.util.modulePath(ProstateCryoAblationConstants.INHERITED_MODULE_NAME))
    self.finishStepIcon = self.createIcon('icon-start.png',
                                          os.path.join(iconPathDir, 'Resources/Icons'))
    self.backIcon = self.createIcon('icon-back.png',
                                    os.path.join(iconPathDir, 'Resources/Icons'))
    super(ProstateCryoAblationTargetingStep, self).__init__()
    self.resetAndInitialize()

  def resetAndInitialize(self):
    self.session.retryMode = False

  def setup(self):
    super(ProstateCryoAblationTargetingStep, self).setup()
    self.setupTargetingPlugin()
    self.setupNavigationButtons()

  def setupTargetingPlugin(self):
    self.targetingPlugin = SliceTrackerTargetingPlugin()
    self.targetingPlugin.addEventObserver(self.targetingPlugin.TargetingStartedEvent, self.onTargetingStarted)
    self.targetingPlugin.addEventObserver(self.targetingPlugin.TargetingFinishedEvent, self.onTargetingFinished)
    self.addPlugin(self.targetingPlugin)
    self.layout().addWidget(self.targetingPlugin)

  def setupNavigationButtons(self):
    iconSize = qt.QSize(36, 36)
    self.backButton = self.createButton("", icon=self.backIcon, iconSize=iconSize,
                                        toolTip="Return to last step")
    self.finishStepButton = self.createButton("", icon=self.finishStepIcon, iconSize=iconSize,
                                              toolTip="Confirm the targeting")
    self.finishStepButton.setFixedHeight(45)
    self.layout().addWidget(self.createHLayout([self.backButton, self.finishStepButton]))

  def onBackButtonClicked(self):
    if self.session.retryMode:
      self.session.retryMode = False
    if self.session.previousStep:
      self.session.previousStep.active = True

  def onFinishStepButtonClicked(self):
    if not self.session.data.usePreopData and not self.session.retryMode:
      self.createCoverProstateRegistrationResultManually()
    else:
      self.session.onInvokeRegistration(initial=True, retryMode=self.session.retryMode)

  def createCoverProstateRegistrationResultManually(self):
    fixedVolume = self.session.currentSeriesVolume
    result = self.session.generateNameAndCreateRegistrationResult(fixedVolume)
    approvedRegistrationType = "rigid" # when no preop image available, we set the first registration result to rigid type
    result.targets.original = self.session.movingTargets
    targetName = str(result.seriesNumber) + '-TARGETS-' + approvedRegistrationType + result.suffix
    clone = self.logic.cloneFiducials(self.session.movingTargets, targetName)
    self.session.applyDefaultTargetDisplayNode(clone)
    result.setTargets(approvedRegistrationType, clone)
    result.volumes.fixed = fixedVolume
    result.labels.fixed = self.session.fixedLabel
    result.approve(approvedRegistrationType)

  def setupConnections(self):
    super(ProstateCryoAblationTargetingStep, self).setupConnections()
    self.backButton.clicked.connect(self.onBackButtonClicked)
    self.finishStepButton.clicked.connect(self.onFinishStepButtonClicked)

  @vtk.calldata_type(vtk.VTK_STRING)
  def onInitiateTargeting(self, caller, event, callData):
    self._initiateTargeting(ast.literal_eval(callData))

  def _initiateTargeting(self, retryMode=False):
    self.resetAndInitialize()
    self.session.retryMode = retryMode
    if self.session.seriesTypeManager.isCoverProstate(self.session.currentSeries):
      if self.session.data.usePreopData:
        if self.session.retryMode:
          if not self.loadLatestCoverProstateResultData():
            self.loadInitialData()
        else:
          self.loadInitialData()
      else:
        self.session.movingVolume = self.session.currentSeriesVolume
    else:
      self.loadLatestCoverProstateResultData()
    self.active = True

  def loadInitialData(self):
    self.session.movingLabel = self.session.data.initialLabel
    self.session.movingVolume = self.session.data.initialVolume
    self.session.movingTargets = self.session.data.initialTargets

  def onActivation(self):
    self.session.fixedVolume = self.session.currentSeriesVolume
    if not self.session.fixedVolume:
      return
    self.updateAvailableLayouts()
    super(ProstateCryoAblationTargetingStep, self).onActivation()

  def updateAvailableLayouts(self):
    pass

  def onDeactivation(self):
    super(ProstateCryoAblationTargetingStep, self).onDeactivation()


  def loadLatestCoverProstateResultData(self):
    coverProstate = self.session.data.getMostRecentApprovedCoverProstateRegistration()
    if coverProstate:
      self.session.movingVolume = coverProstate.volumes.fixed
      self.session.movingLabel = coverProstate.labels.fixed
      self.session.movingTargets = coverProstate.targets.approved
      return True
    return False

  def setupSessionObservers(self):
    super(ProstateCryoAblationTargetingStep, self).setupSessionObservers()
    self.session.addEventObserver(self.session.InitiateSegmentationEvent, self.onInitiateTargeting)

  def removeSessionEventObservers(self):
    super(ProstateCryoAblationTargetingStep, self).removeSessionEventObservers()
    self.session.removeEventObserver(self.session.InitiateSegmentationEvent, self.onInitiateTargeting)


  @vtk.calldata_type(vtk.VTK_STRING)
  def onNewImageSeriesReceived(self, caller, event, callData):
    # TODO: control here to automatically activate the step
    if not self.active:
      return
    newImageSeries = ast.literal_eval(callData)
    for series in reversed(newImageSeries):
      if self.session.seriesTypeManager.isCoverProstate(series):
        if series != self.session.currentSeries:
          if not slicer.util.confirmYesNoDisplay("Another %s was received. Do you want to use this one?"
                                                  % self.getSetting("COVER_PROSTATE")):
            return
          self.session.currentSeries = series
          self._initiateTargeting()
          self.onActivation()
          return


  def onTargetingStarted(self, caller, event):
    self.backButton.enabled = False
    pass

  def onTargetingFinished(self, caller, event):
    self.finishStepButton.enabled = True
    self.backButton.enabled = True
    pass