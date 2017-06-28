import os
import qt
import vtk
import slicer
from ProstateCryoAblationUtils.steps.base import ProstateCryoAblationLogicBase, ProstateCryoAblationStep
from ProstateCryoAblationUtils.steps.plugins.results import ProstateCryoAblationRegistrationResultsLogic, ProstateCryoAblationRegistrationResultsPlugin
from ProstateCryoAblationUtils.steps.plugins.targets import ProstateCryoAblationTargetTablePlugin


class ProstateCryoAblationEvaluationStepLogic(ProstateCryoAblationLogicBase):

  def __init__(self):
    super(ProstateCryoAblationEvaluationStepLogic, self).__init__()


class ProstateCryoAblationEvaluationStep(ProstateCryoAblationStep):

  NAME = "Evaluation"
  LogicClass = ProstateCryoAblationEvaluationStepLogic

  def __init__(self):
    self.modulePath = os.path.dirname(slicer.util.modulePath(self.MODULE_NAME)).replace(".py", "")
    super(ProstateCryoAblationEvaluationStep, self).__init__()

  def setupIcons(self):
    self.retryIcon = self.createIcon("icon-retry.png")
    self.approveIcon = self.createIcon("icon-thumbsUp.png")
    self.rejectIcon = self.createIcon("icon-thumbsDown.png")

  def setup(self):
    super(ProstateCryoAblationEvaluationStep, self).setup()
    self.registrationEvaluationGroupBox = qt.QGroupBox()
    self.registrationEvaluationGroupBoxLayout = qt.QGridLayout()
    self.registrationEvaluationGroupBox.setLayout(self.registrationEvaluationGroupBoxLayout)
    self.setupRegistrationValidationButtons()

    self.regResultsPlugin = ProstateCryoAblationRegistrationResultsPlugin()
    self.addPlugin(self.regResultsPlugin)
    self.regResultsPlugin.addEventObserver(self.regResultsPlugin.RegistrationTypeSelectedEvent,
                                            self.onRegistrationTypeSelected)

    self.targetTablePlugin = ProstateCryoAblationTargetTablePlugin(movingEnabled=True)
    self.addPlugin(self.targetTablePlugin)

    self.registrationEvaluationGroupBoxLayout.addWidget(self.regResultsPlugin, 3, 0)
    self.registrationEvaluationGroupBoxLayout.addWidget(self.targetTablePlugin, 4, 0)
    self.registrationEvaluationGroupBoxLayout.addWidget(self.registrationEvaluationButtonsGroupBox, 5, 0)
    self.registrationEvaluationGroupBoxLayout.setRowStretch(6, 1)
    self.layout().addWidget(self.registrationEvaluationGroupBox)

  def setupRegistrationValidationButtons(self):
    iconSize = qt.QSize(36, 36)
    self.approveRegistrationResultButton = self.createButton("", icon=self.approveIcon, iconSize=iconSize,
                                                             toolTip="Approve")
    self.retryRegistrationButton = self.createButton("", icon=self.retryIcon, iconSize=iconSize, toolTip="Retry")
    self.rejectRegistrationResultButton = self.createButton("", icon=self.rejectIcon, iconSize=iconSize,
                                                            toolTip="Reject")
    self.registrationEvaluationButtonsGroupBox = self.createHLayout([self.retryRegistrationButton,
                                                                     self.approveRegistrationResultButton,
                                                                     self.rejectRegistrationResultButton])

  def setupConnections(self):
    self.retryRegistrationButton.clicked.connect(self.onRetryRegistrationButtonClicked)
    self.approveRegistrationResultButton.clicked.connect(self.onApproveRegistrationResultButtonClicked)
    self.rejectRegistrationResultButton.clicked.connect(self.onRejectRegistrationResultButtonClicked)
    # self.registrationDetailsButton.clicked.connect(self.onShowRegistrationDetails)

  def setupSessionObservers(self):
    super(ProstateCryoAblationEvaluationStep, self).setupSessionObservers()
    self.session.addEventObserver(self.session.InitiateEvaluationEvent, self.onInitiateEvaluation)

  def removeSessionEventObservers(self):
    super(ProstateCryoAblationEvaluationStep, self).removeSessionEventObservers()
    self.session.removeEventObserver(self.session.InitiateEvaluationEvent, self.onInitiateEvaluation)

  def onRetryRegistrationButtonClicked(self):
    self.session.retryRegistration()

  def onApproveRegistrationResultButtonClicked(self):
    results = self.session.data.getResultsBySeriesNumber(self.currentResult.seriesNumber)
    for result in [r for r in results if r is not self.currentResult]:
      result.reject()
    self.currentResult.approve(registrationType=self.regResultsPlugin.registrationButtonGroup.checkedButton().name)
    # if self.ratingWindow.isRatingEnabled():
    #   self.ratingWindow.show(disableWidget=self.parent)

  def onRejectRegistrationResultButtonClicked(self):
    results = self.session.data.getResultsBySeriesNumber(self.currentResult.seriesNumber)
    for result in [r for r in results if r is not self.currentResult]:
      result.reject()
    self.currentResult.reject()

  def onInitiateEvaluation(self, caller, event):
    self.active = True

  def onActivation(self):
    super(ProstateCryoAblationEvaluationStep, self).onActivation()
    self.enabled = self.currentResult is not None
    if not self.currentResult:
      return
    # self.redOnlyLayoutButton.enabled = False
    # self.sideBySideLayoutButton.enabled = True
    self.rejectRegistrationResultButton.enabled = not self.session.seriesTypeManager.isCoverProstate(self.currentResult.name)
    self.currentResult.save(self.session.outputDirectory)
    self.currentResult.printSummary()
    if not self.logic.isVolumeExtentValid(self.currentResult.volumes.bSpline):
      slicer.util.infoDisplay(
        "One or more empty volume were created during registration process. You have three options:\n"
        "1. Reject the registration result \n"
        "2. Retry with creating a new segmentation \n"
        "3. Set targets to your preferred position (in Four-Up layout)",
        title="Action needed: Registration created empty volume(s)", windowTitle="ProstateCryoAblation")

  def onDeactivation(self):
    super(ProstateCryoAblationEvaluationStep, self).onDeactivation()
    self.hideAllLabels()
    self.hideAllFiducialNodes()

  @vtk.calldata_type(vtk.VTK_STRING)
  def onRegistrationTypeSelected(self, caller, event, callData):
    self.targetTablePlugin.currentTargets = getattr(self.currentResult.targets, callData)