import os
import ast
import qt
import slicer
import vtk
from ProstateAblationUtils.steps.base import ProstateAblationLogicBase,ProstateAblationStep

class ProstateAblationTargetingStepLogic(ProstateAblationLogicBase):
  
  def __init__(self, prostateCryoSession):
    super(ProstateAblationTargetingStepLogic, self).__init__(prostateCryoSession)
        
class ProstateAblationTargetingStep(ProstateAblationStep):

  NAME = "Targeting"
  LogicClass = ProstateAblationTargetingStepLogic
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

  def __init__(self, ProstateAblationSession):
    super(ProstateAblationTargetingStep, self).__init__(ProstateAblationSession)
    rootSciptModuleDir = os.path.abspath(os.path.join(slicer.modules.segmenteditor.path, os.pardir))
    iconDir = os.path.join(rootSciptModuleDir, "Resources", "Icons")
    self.gotoSegmentationIcon = self.createIcon('SegmentEditor.png', iconDir)
    self.gotoSegmentationButton = self.createButton("", icon=self.gotoSegmentationIcon, iconSize=self.iconSize,
                                        toolTip="Go To Segmentaion Step")
    self.gotoTargetingIcon = self.createIcon('Fiducials.png', iconDir)
    self.gotoTargetingButton = self.createButton("", icon=self.gotoTargetingIcon, iconSize=self.iconSize,
                                                    toolTip="Go To Targeting Step")
    self.gotoSegmentationButton.clicked.connect(self.onGoToSegmentButtonClicked)
    self.gotoTargetingButton.clicked.connect(self.onGoToTargetingButtonClicked)
    self._NeedleType = self.ICESEED

  def setup(self):
    super(ProstateAblationTargetingStep, self).setup()
    self.setupTargetingPlugin()
    self.addPlugin(self.session.targetingPlugin)
    self.layout().addStretch()

  def setupTargetingPlugin(self):
    self.session.targetingPlugin.addEventObserver(self.session.targetingPlugin.TargetingStartedEvent, self.onTargetingStarted)
    self.session.targetingPlugin.addEventObserver(self.session.targetingPlugin.TargetingFinishedEvent, self.onTargetingFinished)
  
  def onBackButtonClicked(self):
    if self.session.previousStep:
      self.session.previousStep.active = True

  def onGoToSegmentButtonClicked(self):
    self.session.targetingPlugin.targetingGroupBox.visible = False
    self.gotoSegmentationButton.visible = False
    self.session.segmentationEditor.visible = True
    self.layout().addWidget(self.session.segmentationEditor)
    self.addSegNavigationButtons()

  def onGoToTargetingButtonClicked(self):
    self.session.segmentationEditor.visible = False
    self.gotoTargetingButton.visible = False
    self.session.targetingPlugin.targetingGroupBox.visible = True
    self.layout().addWidget(self.session.targetingPlugin.targetingGroupBox)
    self.addTargetingNavigationButtons()

  def onFinishStepButtonClicked(self):
    #To do, deactivate the drawing buttons when finish button clicked
    self.session.data.segmentModelNode = self.session.segmentationEditor.segmentationNode()
    self.session.segmentationEditorNoneButton.click()
    self.session.previousStep.active = True
  
  def setupConnections(self):
    super(ProstateAblationTargetingStep, self).setupConnections()
    self.backButton.clicked.connect(self.onBackButtonClicked)
    self.finishStepButton.clicked.connect(self.onFinishStepButtonClicked)
    
  def onActivation(self):
    super(ProstateAblationTargetingStep, self).onActivation()
    if not self.session.currentSeriesVolume:
      return
    self.updateAvailableLayouts()
    self.setupFourUpView(self.session.currentSeriesVolume)
    self.session.segmentationEditor.setSegmentationNode(self.session.data.segmentModelNode)
    self.session.segmentationEditor.setMasterVolumeNode(self.session.currentSeriesVolume)
    self.session.targetingPlugin.targetingGroupBox.visible = True
    self.session.targetingPlugin.fiducialsWidget.visible = True
    self.session.targetingPlugin.fiducialsWidget.table.visible = False
    self.onGoToTargetingButtonClicked()

  def addTargetingNavigationButtons(self):
    self.gotoSegmentationButton.visible = True
    self.layout().addWidget(self.createHLayout([self.backButton, self.gotoSegmentationButton, self.finishStepButton]))

  def addSegNavigationButtons(self):
    self.gotoTargetingButton.visible = True
    self.layout().addWidget(self.createHLayout([self.backButton, self.gotoTargetingButton, self.finishStepButton]))

  def updateAvailableLayouts(self):
    pass

  def onDeactivation(self):
    super(ProstateAblationTargetingStep, self).onDeactivation()

  def addSessionObservers(self):
    super(ProstateAblationTargetingStep, self).addSessionObservers()
    self.session.addEventObserver(self.session.InitiateTargetingEvent, self.onInitiateTargeting)

  def removeSessionEventObservers(self):
    super(ProstateAblationTargetingStep, self).removeSessionEventObservers()
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