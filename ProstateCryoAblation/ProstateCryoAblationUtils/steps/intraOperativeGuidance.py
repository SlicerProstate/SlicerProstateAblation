import os
import ast
import qt
import slicer
import vtk
from ..UserEvents import ProstateCryoAblationUserEvents
from ..constants import ProstateCryoAblationConstants
from ProstateCryoAblationUtils.steps.base import ProstateCryoAblationLogicBase,ProstateCryoAblationStep
from ProstateCryoAblationUtils.steps.plugins.targeting import ProstateCryoAblationTargetingPlugin
from SlicerDevelopmentToolboxUtils.helpers import SliceAnnotation
from SlicerDevelopmentToolboxUtils.decorators import onModuleSelected
from SlicerDevelopmentToolboxUtils.mixins import ModuleLogicMixin
from SlicerDevelopmentToolboxUtils.icons import Icons

class ProstateCryoAblationGuidanceStepLogic(ProstateCryoAblationLogicBase): # make it the same as overview for now

  def __init__(self):
    super(ProstateCryoAblationGuidanceStepLogic, self).__init__()
    self.GuidanceVolume = None


class ProstateCryoAblationGuidanceStep(ProstateCryoAblationStep):

  NAME = "Guidance"
  LogicClass = ProstateCryoAblationGuidanceStepLogic

  def __init__(self):
    self.notifyUserAboutNewData = True
    iconPathDir = os.path.dirname(slicer.util.modulePath(ProstateCryoAblationConstants.MODULE_NAME))
    self.finishStepIcon = Icons.start
    self.backIcon = Icons.back
    super(ProstateCryoAblationGuidanceStep, self).__init__()


  def setup(self):
    super(ProstateCryoAblationGuidanceStep, self).setup()
    self.targetingPlugin = ProstateCryoAblationTargetingPlugin()
    self.addPlugin(self.targetingPlugin)
    self.layout().addWidget(self.targetingPlugin)
    self.setupNavigationButtons()


  def setupNavigationButtons(self):
    iconSize = qt.QSize(36, 36)
    self.backButton = self.createButton("", icon=self.backIcon, iconSize=iconSize,
                                        toolTip="Return to last step")
    self.finishStepButton = self.createButton("", icon=self.finishStepIcon, iconSize=iconSize,
                                              toolTip="Confirm the targeting")
    self.finishStepButton.setFixedHeight(45)
    self.layout().addWidget(self.createHLayout([self.backButton, self.finishStepButton]))

  def onBackButtonClicked(self):
    if self.session.previousStep:
      self.session.previousStep.active = True

  def onFinishStepButtonClicked(self):
    self.session.previousStep.active = True

  def setupConnections(self):
    super(ProstateCryoAblationGuidanceStep, self).setupConnections()

  def addSessionObservers(self):
    super(ProstateCryoAblationGuidanceStep, self).addSessionObservers()
    self.session.addEventObserver(self.session.NeedleGuidanceEvent, self.onNeedleGuidance)
    self.backButton.clicked.connect(self.onBackButtonClicked)
    self.finishStepButton.clicked.connect(self.onFinishStepButtonClicked)

  def removeSessionEventObservers(self):
    ProstateCryoAblationStep.removeSessionEventObservers(self)
    self.session.removeEventObserver(self.session.NeedleGuidanceEvent, self.onNeedleGuidance)

  def onActivation(self):
    super(ProstateCryoAblationGuidanceStep, self).onActivation()
    self.layoutManager.setLayout(ProstateCryoAblationConstants.LAYOUT_FOUR_UP)
    if self.logic.GuidanceVolume :
      self.setupFourUpView(self.logic.GuidanceVolume)


  def onDeactivation(self):
    super(ProstateCryoAblationGuidanceStep, self).onDeactivation()
    self.logic.GuidanceVolume = None

  def onNeedleGuidance(self, caller, event):
    print "need guidance in action"
    self.logic.GuidanceVolume = self.session.currentSeriesVolume
    self.active = True
    pass

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
                                                     % self.getSetting("NEEDLE_IMAGE")):
            return
          self.session.currentSeries = series
          self.onNeedleGuidance()
          self.onActivation()
          return