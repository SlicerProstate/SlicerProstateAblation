import ast
import logging
import os

import ctk
import qt
import slicer
import vtk
from SlicerDevelopmentToolboxUtils.constants import COLOR
from SlicerDevelopmentToolboxUtils.decorators import logmethod, onReturnProcessEvents, processEventsEvery
from SlicerDevelopmentToolboxUtils.widgets import CustomStatusProgressbar
from base import ProstateCryoAblationLogicBase, ProstateCryoAblationStep
from ProstateCryoAblationUtils.steps.plugins.case import ProstateCryoAblationCaseManagerPlugin
from ProstateCryoAblationUtils.steps.plugins.targeting import ProstateCryoAblationTargetingPlugin
from ProstateCryoAblationUtils.steps.plugins.training import ProstateCryoAblationTrainingPlugin
from ..constants import ProstateCryoAblationConstants as constants
from ..helpers import IncomingDataMessageBox, SeriesTypeToolButton, SeriesTypeManager
from SlicerDevelopmentToolboxUtils.icons import Icons

class ProstateCryoAblationOverViewStepLogic(ProstateCryoAblationLogicBase):

  def __init__(self):
    super(ProstateCryoAblationOverViewStepLogic, self).__init__()

  def applyBiasCorrection(self):
    outputVolume = slicer.vtkMRMLScalarVolumeNode()
    outputVolume.SetName('VOLUME-PREOP-N4')
    slicer.mrmlScene.AddNode(outputVolume)
    params = {'inputImageName': self.session.data.initialVolume.GetID(),
              'maskImageName': self.session.data.initialLabel.GetID(),
              'outputImageName': outputVolume.GetID(),
              'numberOfIterations': '500,400,300'}

    slicer.cli.run(slicer.modules.n4itkbiasfieldcorrection, None, params, wait_for_completion=True)
    self.session.data.initialVolume = outputVolume
    self.session.data.biasCorrectionDone = True


class ProstateCryoAblationOverviewStep(ProstateCryoAblationStep):

  NAME = "Overview"
  LogicClass = ProstateCryoAblationOverViewStepLogic
  LayoutClass = qt.QVBoxLayout
  def __init__(self):
    super(ProstateCryoAblationOverviewStep, self).__init__()
    self.notifyUserAboutNewData = True

  def cleanup(self):
    self._seriesModel.clear()
    self.changeSeriesTypeButton.enabled = False
    self.trackTargetsButton.enabled = False
    self.skipIntraopSeriesButton.enabled = False
    self.updateIntraopSeriesSelectorTable()
    slicer.mrmlScene.Clear(0)

  def setupIcons(self):
    self.trackIcon = self.createIcon('icon-track.png')
    self.skipIcon = Icons.skip #self.createIcon('icon-skip.png')

  def setup(self):
    super(ProstateCryoAblationOverviewStep, self).setup()
    iconSize = qt.QSize(24, 24)
    self.caseManagerPlugin = ProstateCryoAblationCaseManagerPlugin()
    self.trainingPlugin = ProstateCryoAblationTrainingPlugin()


    self.changeSeriesTypeButton = SeriesTypeToolButton()
    self.trackTargetsButton = self.createButton("", icon=self.trackIcon, iconSize=iconSize, toolTip="Track targets",
                                                enabled=False)
    self.skipIntraopSeriesButton = self.createButton("", icon=self.skipIcon, iconSize=iconSize,
                                                     toolTip="Skip selected series", enabled=False)
    self.setupIntraopSeriesSelector()

    self.targetingPlugin = ProstateCryoAblationTargetingPlugin()
    self.addPlugin(self.targetingPlugin)
    self.targetingPlugin.targetTablePlugin.currentTargets = self.session.movingTargets
    self.layout().addWidget(self.caseManagerPlugin)
    self.layout().addWidget(self.trainingPlugin)
    self.layout().addWidget(self.targetingPlugin.targetTablePlugin)
    self.layout().addWidget(self.createHLayout([self.intraopSeriesSelector, self.changeSeriesTypeButton,
                                                self.trackTargetsButton, self.skipIntraopSeriesButton]))
    self.layout().addStretch(1)

  def setupIntraopSeriesSelector(self):
    self.intraopSeriesSelector = qt.QComboBox()
    self.intraopSeriesSelector.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Minimum)
    self._seriesModel = qt.QStandardItemModel()
    self.intraopSeriesSelector.setModel(self._seriesModel)
    self.intraopSeriesSelector.setToolTip(constants.IntraopSeriesSelectorToolTip)

  def setupConnections(self):
    super(ProstateCryoAblationOverviewStep, self).setupConnections()
    self.skipIntraopSeriesButton.clicked.connect(self.onSkipIntraopSeriesButtonClicked)
    self.trackTargetsButton.clicked.connect(self.onTrackTargetsButtonClicked)
    self.intraopSeriesSelector.connect('currentIndexChanged(QString)', self.onIntraopSeriesSelectionChanged)

  def addSessionObservers(self):
    super(ProstateCryoAblationOverviewStep, self).addSessionObservers()
    self.session.addEventObserver(self.session.SeriesTypeManuallyAssignedEvent, self.onSeriesTypeManuallyAssigned)
    self.session.addEventObserver(self.session.ZFrameRegistrationSuccessfulEvent, self.onZFrameRegistrationSuccessful)

  def removeSessionEventObservers(self):
    ProstateCryoAblationStep.removeSessionEventObservers(self)
    self.session.removeEventObserver(self.session.SeriesTypeManuallyAssignedEvent, self.onSeriesTypeManuallyAssigned)
    self.session.removeEventObserver(self.session.ZFrameRegistrationSuccessfulEvent, self.onZFrameRegistrationSuccessful)

  def onSkipIntraopSeriesButtonClicked(self):
    if slicer.util.confirmYesNoDisplay("Do you really want to skip this series?", windowTitle="Skip series?"):
      self.updateIntraopSeriesSelectorTable()

  def onTrackTargetsButtonClicked(self):
    self.session.takeActionForCurrentSeries()

  @logmethod(logging.INFO)
  def onIntraopSeriesSelectionChanged(self, selectedSeries=None):
    self.session.currentSeries = selectedSeries
    if selectedSeries:
      trackingPossible = self.session.isTrackingPossible(selectedSeries)
      self.setIntraopSeriesButtons(trackingPossible, selectedSeries)
      self.changeSeriesTypeButton.setSeries(selectedSeries)
    colorStyle = self.session.getColorForSelectedSeries(self.intraopSeriesSelector.currentText)
    self.intraopSeriesSelector.setStyleSheet("QComboBox{%s} QToolTip{background-color: white;}" % colorStyle)

  def setIntraopSeriesButtons(self, trackingPossible, selectedSeries):
    trackingPossible = trackingPossible and not self.session.data.completed
    #self.changeSeriesTypeButton.enabled = not self.session.data.exists(selectedSeries) # TODO: take zFrameRegistration into account
    self.trackTargetsButton.enabled = trackingPossible
    self.skipIntraopSeriesButton.enabled = trackingPossible and self.session.isEligibleForSkipping(selectedSeries)

  @vtk.calldata_type(vtk.VTK_STRING)
  def onCurrentSeriesChanged(self, caller, event, callData=None):
    logging.info("Current series selection changed invoked from session")
    logging.info("Series with name %s selected" % callData if callData else "")
    if callData:
      model = self.intraopSeriesSelector.model()
      index = next((i for i in range(model.rowCount()) if model.item(i).text() == callData), None)
      self.intraopSeriesSelector.currentIndex = index

  @logmethod(logging.INFO)
  def onZFrameRegistrationSuccessful(self, caller, event):
    self.active = True

  @vtk.calldata_type(vtk.VTK_STRING)
  def onFailedPreProcessing(self, caller, event, callData):
    if slicer.util.confirmYesNoDisplay(callData, windowTitle="ProstateCryoAblation"):
      self.startPreProcessingModule()
    else:
      self.session.close()

  @logmethod(logging.INFO)
  def onRegistrationStatusChanged(self, caller, event):
    self.active = True

  def onLoadingMetadataSuccessful(self, caller, event):
    self.active = True

  @vtk.calldata_type(vtk.VTK_STRING)
  def onCaseClosed(self, caller, event, callData):
    if callData != "None":
      slicer.util.infoDisplay(callData, windowTitle="ProstateCryoAblation")
    self.cleanup()

  def onPreprocessingSuccessful(self, caller, event):
    self.configureRedSliceNodeForPreopData()
    self.promptUserAndApplyBiasCorrectionIfNeeded()

  def onActivation(self):
    super(ProstateCryoAblationOverviewStep, self).onActivation()
    self.updateIntraopSeriesSelectorTable()

  def onSeriesTypeManuallyAssigned(self, caller, event):
    self.updateIntraopSeriesSelectorTable()

  @logmethod(logging.INFO)
  def onPreopReceptionFinished(self, caller=None, event=None):
    if self.invokePreProcessing():
      self.startPreProcessingModule()
    else:
      slicer.util.infoDisplay("No DICOM data could be processed. Please select another directory.",
                              windowTitle="ProstateCryoAblation")

  def startPreProcessingModule(self):
    self.setSetting('InputLocation', None, moduleName="mpReview")
    self.layoutManager.selectModule("mpReview")
    mpReview = slicer.modules.mpReviewWidget
    self.setSetting('InputLocation', self.session.preprocessedDirectory, moduleName="mpReview")
    mpReview.onReload()
    slicer.modules.mpReviewWidget.saveButton.clicked.connect(self.returnFromPreProcessingModule)
    self.layoutManager.selectModule(mpReview.moduleName)

  def returnFromPreProcessingModule(self):
    slicer.modules.mpReviewWidget.saveButton.clicked.disconnect(self.returnFromPreProcessingModule)
    self.layoutManager.selectModule(self.MODULE_NAME)
    slicer.mrmlScene.Clear(0)
    self.session.loadPreProcessedData()

  def invokePreProcessing(self):
    if not os.path.exists(self.session.preprocessedDirectory):
      self.logic.createDirectory(self.session.preprocessedDirectory)
    from mpReviewPreprocessor import mpReviewPreprocessorLogic
    self.mpReviewPreprocessorLogic = mpReviewPreprocessorLogic()
    progress = self.createProgressDialog()
    progress.canceled.connect(self.mpReviewPreprocessorLogic.cancelProcess)

    @onReturnProcessEvents
    def updateProgressBar(**kwargs):
      for key, value in kwargs.iteritems():
        if hasattr(progress, key):
          setattr(progress, key, value)

    self.mpReviewPreprocessorLogic.importStudy(self.session.preopDICOMDirectory, progressCallback=updateProgressBar)
    success = False
    if self.mpReviewPreprocessorLogic.patientFound():
      success = True
      self.mpReviewPreprocessorLogic.processData(outputDir=self.session.preprocessedDirectory, copyDICOM=False,
                                                 progressCallback=updateProgressBar)
    progress.canceled.disconnect(self.mpReviewPreprocessorLogic.cancelProcess)
    progress.close()
    return success

  @vtk.calldata_type(vtk.VTK_STRING)
  def onNewImageSeriesReceived(self, caller, event, callData):
    if not self.session.isLoading():
      customStatusProgressBar = CustomStatusProgressbar()
      customStatusProgressBar.text = "New image data has been received."

    self.updateIntraopSeriesSelectorTable()

    if not self.active or self.session.isLoading():
      return
    selectedSeries = self.intraopSeriesSelector.currentText
    if selectedSeries != "" and self.session.isTrackingPossible(selectedSeries):
      selectedSeriesNumber = int(selectedSeries.split(": ")[0])

      newImageSeries = ast.literal_eval(callData)
      newImageSeriesNumbers = [int(s.split(": ")[0]) for s in newImageSeries]
      if selectedSeriesNumber in newImageSeriesNumbers:
        self.takeActionOnSelectedSeries()

  def onCaseOpened(self, caller, event):
    if self.active and not self.session.isLoading():
      self.selectMostRecentEligibleSeries()
      self.takeActionOnSelectedSeries()

  def takeActionOnSelectedSeries(self):
    selectedSeries = self.intraopSeriesSelector.currentText
    if self.session.seriesTypeManager.isCoverTemplate(selectedSeries) and not self.session.zFrameRegistrationSuccessful:
      self.onTrackTargetsButtonClicked()
      return

  def updateIntraopSeriesSelectorTable(self):
    self.intraopSeriesSelector.blockSignals(True)
    currentIndex = self.intraopSeriesSelector.currentIndex
    self._seriesModel.clear()
    for series in self.session.seriesList:
      sItem = qt.QStandardItem(series)
      self._seriesModel.appendRow(sItem)
      color = COLOR.GREEN
      self._seriesModel.setData(sItem.index(), color, qt.Qt.BackgroundRole)
    self.intraopSeriesSelector.setCurrentIndex(currentIndex)
    self.intraopSeriesSelector.blockSignals(False)
    colorStyle = self.session.getColorForSelectedSeries(self.intraopSeriesSelector.currentText)
    self.intraopSeriesSelector.setStyleSheet("QComboBox{%s} QToolTip{background-color: white;}" % colorStyle)
    if self.active and not self.session.isLoading():
      self.selectMostRecentEligibleSeries()

  def selectMostRecentEligibleSeries(self):
    substring = self.getSetting("NEEDLE_IMAGE")
    seriesTypeManager = SeriesTypeManager()
    self.intraopSeriesSelector.blockSignals(True)
    self.intraopSeriesSelector.setCurrentIndex(-1)
    self.intraopSeriesSelector.blockSignals(False)
    index = -1
    for item in list(reversed(range(len(self.session.seriesList)))):
      series = self._seriesModel.item(item).text()
      if substring in seriesTypeManager.getSeriesType(series):
        index = self.intraopSeriesSelector.findText(series)
        break
      elif self.session.seriesTypeManager.isVibe(series) and index == -1:
        index = self.intraopSeriesSelector.findText(series)
    rowCount = self.intraopSeriesSelector.model().rowCount()

    self.intraopSeriesSelector.setCurrentIndex(index if index != -1 else (rowCount-1 if rowCount else -1))

  def configureRedSliceNodeForPreopData(self):
    if not self.session.data.initialVolume or not self.session.data.initialTargets:
      return
    self.layoutManager.setLayout(constants.LAYOUT_RED_SLICE_ONLY)
    self.redSliceNode.SetOrientationToAxial()
    self.redSliceNode.RotateToVolumePlane(self.session.data.initialVolume)
    self.redSliceNode.SetUseLabelOutline(True)
    self.redCompositeNode.SetLabelOpacity(1)
    self.targetingPlugin.targetTablePlugin.currentTargets = self.session.data.initialTargets

  def promptUserAndApplyBiasCorrectionIfNeeded(self):
    if not self.session.data.resumed and not self.session.data.completed:
      if slicer.util.confirmYesNoDisplay("Was an endorectal coil used for preop image acquisition?",
                                         windowTitle="ProstateCryoAblation"):
        customProgressbar = CustomStatusProgressbar()
        customProgressbar.busy = True
        currentModule = slicer.util.getModuleGui(self.MODULE_NAME)
        if currentModule:
          currentModule.parent().enabled = False
        try:
          customProgressbar.updateStatus("Bias correction running!")
          slicer.app.processEvents()
          self.logic.applyBiasCorrection()
        except AttributeError:
          pass
        finally:
          customProgressbar.busy = False
          if currentModule:
            currentModule.parent().enabled = True
        customProgressbar.updateStatus("Bias correction done!")