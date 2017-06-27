import os
import ast
import qt
import slicer
import vtk
from ..UserEvents import ProstateCryoAblationUserEvents
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
    super(ProstateCryoAblationTargetingStep, self).__init__()
    self.resetAndInitialize()

  def resetAndInitialize(self):
    self.session.retryMode = False

  def setup(self):
    super(ProstateCryoAblationTargetingStep, self).setup()
    self.setupTargetingPlugin()

  def setupTargetingPlugin(self):
    self.targetingPlugin = SliceTrackerTargetingPlugin()
    self.targetingPlugin.addEventObserver(self.targetingPlugin.TargetingStartedEvent, self.onTargetingStarted)
    self.targetingPlugin.addEventObserver(self.targetingPlugin.TargetingFinishedEvent, self.onTargetingFinished)
    self.addPlugin(self.targetingPlugin)
    self.layout().addWidget(self.targetingPlugin)

  def setupConnections(self):
    super(ProstateCryoAblationTargetingStep, self).setupConnections()

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

  def inputsAreSet(self):
    return self.session.fixedVolume is not None and self.session.fixedLabel is not None \
             and self.session.movingTargets is not None

  def onTargetingStarted(self, caller, event):
    pass

  def onTargetingFinished(self, caller, event):
    pass