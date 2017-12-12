import os
import ast
import qt
import slicer
import vtk
from ..constants import ProstateCryoAblationConstants
from ProstateCryoAblationUtils.steps.base import ProstateCryoAblationLogicBase,ProstateCryoAblationStep

class ProstateCryoAblationGuidanceStepLogic(ProstateCryoAblationLogicBase): # make it the same as overview for now

  def __init__(self, prostateCryoAblationSession):
    super(ProstateCryoAblationGuidanceStepLogic, self).__init__(prostateCryoAblationSession)
    self.GuidanceVolume = None


class ProstateCryoAblationGuidanceStep(ProstateCryoAblationStep):

  NAME = "Guidance"
  LogicClass = ProstateCryoAblationGuidanceStepLogic
  LayoutClass = qt.QVBoxLayout
  def __init__(self, prostateCryoAblationSession):
    self.notifyUserAboutNewData = True
    super(ProstateCryoAblationGuidanceStep, self).__init__(prostateCryoAblationSession)

  def setup(self):
    super(ProstateCryoAblationGuidanceStep, self).setup()

  def onBackButtonClicked(self):
    if self.session.previousStep:
      self.session.previousStep.active = True

  def onFinishStepButtonClicked(self):
    self.session.previousStep.active = True

  def setupConnections(self):
    super(ProstateCryoAblationGuidanceStep, self).setupConnections()
    self.backButton.clicked.connect(self.onBackButtonClicked)
    self.finishStepButton.clicked.connect(self.onFinishStepButtonClicked)

  def addSessionObservers(self):
    super(ProstateCryoAblationGuidanceStep, self).addSessionObservers()
    self.session.addEventObserver(self.session.NeedleGuidanceEvent, self.onNeedleGuidance)

  def removeSessionEventObservers(self):
    ProstateCryoAblationStep.removeSessionEventObservers(self)
    self.session.removeEventObserver(self.session.NeedleGuidanceEvent, self.onNeedleGuidance)

  def onActivation(self):
    super(ProstateCryoAblationGuidanceStep, self).onActivation()
    self.layoutManager.setLayout(ProstateCryoAblationConstants.LAYOUT_FOUR_UP)
    if self.logic.GuidanceVolume :
      self.setupFourUpView(self.logic.GuidanceVolume)
      self.layout().addWidget(self.session.targetingPlugin.targetingGroupBox)
      self.session.targetingPlugin.targetingGroupBox.visible = True
      self.session.targetingPlugin.fiducialsWidget.visible = False
      self.session.targetingPlugin.targetTablePlugin.visible = True
      self.session.targetingPlugin.targetDistanceWidget.visible = True
      self.addNavigationButtons()
      self.layout().addStretch()

  def onDeactivation(self):
    super(ProstateCryoAblationGuidanceStep, self).onDeactivation()
    self.logic.GuidanceVolume = None

  def onNeedleGuidance(self, caller, event):
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