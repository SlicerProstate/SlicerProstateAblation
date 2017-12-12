import os
import ast
import qt
import slicer
import vtk
from ProstateCryoAblationUtils.steps.base import ProstateCryoAblationLogicBase,ProstateCryoAblationStep

class ProstateCryoAblationTargetingStepLogic(ProstateCryoAblationLogicBase):
  
  def __init__(self, prostateCryoSession):
    super(ProstateCryoAblationTargetingStepLogic, self).__init__(prostateCryoSession)
        
class ProstateCryoAblationTargetingStep(ProstateCryoAblationStep):

  NAME = "Targeting"
  LogicClass = ProstateCryoAblationTargetingStepLogic
  LayoutClass = qt.QVBoxLayout
  HIDENEEDLE = 0
  ICESEED = 1
  ICEROD = 2
  @property
  def NeedleType(self):
    return self._NeedleType

  @NeedleType.setter
  def NeedleType(self, type):
    self._NeedleType = type

  def __init__(self, prostateCryoAblationSession):
    super(ProstateCryoAblationTargetingStep, self).__init__(prostateCryoAblationSession)
    self._NeedleType = self.ICESEED
    self.tabWidget = qt.QTabWidget()
    self.layout().addWidget(self.tabWidget)

  def setup(self):
    super(ProstateCryoAblationTargetingStep, self).setup()
    self.setupTargetingPlugin()
    self.addPlugin(self.session.targetingPlugin)
    self.layout().addStretch()

  def setupTargetingPlugin(self):
    #self.targetingPlugin = ProstateCryoAblationTargetsDefinitionPlugin()
    self.session.targetingPlugin.addEventObserver(self.session.targetingPlugin.TargetingStartedEvent, self.onTargetingStarted)
    self.session.targetingPlugin.addEventObserver(self.session.targetingPlugin.TargetingFinishedEvent, self.onTargetingFinished)
  
  def onBackButtonClicked(self):
    if self.session.previousStep:
      self.session.previousStep.active = True

  def onFinishStepButtonClicked(self):
    #To do, deactivate the drawing buttons when finish button clicked
    self.session.data.segmentModelNode = self.session.segmentationEditor.segmentationNode()
    self.session.segmentationEditorNoneButton.click()
    self.session.previousStep.active = True
  
  def setupConnections(self):
    super(ProstateCryoAblationTargetingStep, self).setupConnections()
    self.backButton.clicked.connect(self.onBackButtonClicked)
    self.finishStepButton.clicked.connect(self.onFinishStepButtonClicked)

  def onActivation(self):
    super(ProstateCryoAblationTargetingStep, self).onActivation()
    if not self.session.currentSeriesVolume:
      return
    self.updateAvailableLayouts()
    self.setupFourUpView(self.session.currentSeriesVolume)
    self.session.segmentationEditor.setSegmentationNode(self.session.data.segmentModelNode)
    self.session.segmentationEditor.setMasterVolumeNode(self.session.currentSeriesVolume)
    self.session.targetingPlugin.targetingGroupBox.visible = True
    self.session.targetingPlugin.fiducialsWidget.visible = True
    self.session.targetingPlugin.fiducialsWidget.table.visible = False
    self.tabWidget.addTab(self.session.targetingPlugin.targetingGroupBox, "")
    self.tabWidget.addTab(self.session.segmentationEditor, "")
    self.addNavigationButtons()

  def updateAvailableLayouts(self):
    pass

  def onDeactivation(self):
    super(ProstateCryoAblationTargetingStep, self).onDeactivation()

  def addSessionObservers(self):
    super(ProstateCryoAblationTargetingStep, self).addSessionObservers()
    self.session.addEventObserver(self.session.InitiateTargetingEvent, self.onInitiateTargeting)

  def removeSessionEventObservers(self):
    super(ProstateCryoAblationTargetingStep, self).removeSessionEventObservers()
    self.session.removeEventObserver(self.session.InitiateTargetingEvent, self.onInitiateTargeting)

  def onInitiateTargeting(self, caller, event):
    self.active = True

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
          self.onActivation()
          return


  def onTargetingStarted(self, caller, event):
    if self.session.targetingPlugin.targetTablePlugin.currentTargets:
      self.session.targetingPlugin.targetTablePlugin.currentTargets.SetLocked(False)
    self.backButton.enabled = False
    pass

  def onTargetingFinished(self, caller, event):
    if self.session.targetingPlugin.targetTablePlugin.currentTargets:
      self.session.targetingPlugin.targetTablePlugin.currentTargets.SetLocked(True)
    self.finishStepButton.enabled = True
    self.backButton.enabled = True
    pass