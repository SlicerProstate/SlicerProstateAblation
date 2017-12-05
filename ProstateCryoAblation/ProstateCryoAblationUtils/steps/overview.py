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
from ProstateCryoAblationUtils.steps.plugins.training import ProstateCryoAblationTrainingPlugin
from ..constants import ProstateCryoAblationConstants as constants
from ..helpers import SeriesTypeManager
from SlicerDevelopmentToolboxUtils.icons import Icons

class ProstateCryoAblationOverViewStepLogic(ProstateCryoAblationLogicBase):

  def __init__(self, prostateCryoAblationSession):
    super(ProstateCryoAblationOverViewStepLogic, self).__init__(prostateCryoAblationSession)

class ProstateCryoAblationOverviewStep(ProstateCryoAblationStep):

  NAME = "Overview"
  LogicClass = ProstateCryoAblationOverViewStepLogic
  LayoutClass = qt.QVBoxLayout
  def __init__(self, prostateCryoAblationSession):
    super(ProstateCryoAblationOverviewStep, self).__init__(prostateCryoAblationSession)
    self.notifyUserAboutNewData = True
    
  def cleanup(self):
    self._seriesModel.clear()
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
    self.caseManagerPlugin = ProstateCryoAblationCaseManagerPlugin(self.session)
    self.trainingPlugin = ProstateCryoAblationTrainingPlugin(self.session)

    self.trackTargetsButton = self.createButton("", icon=self.trackIcon, iconSize=iconSize, toolTip="Track targets",
                                                enabled=False)
    self.skipIntraopSeriesButton = self.createButton("", icon=self.skipIcon, iconSize=iconSize,
                                                     toolTip="Skip selected series", enabled=False)
    self.setupIntraopSeriesSelector()
    self.layout().addWidget(self.caseManagerPlugin)
    self.addPlugin(self.caseManagerPlugin)
    self.layout().addWidget(self.trainingPlugin)
    self.addPlugin(self.trainingPlugin)
    self.addPlugin(self.session.targetingPlugin)
    self.layout().addWidget(self.session.targetingPlugin.targetTablePlugin)
    self.layout().addWidget(self.createHLayout([self.intraopSeriesSelector, self.trackTargetsButton, self.skipIntraopSeriesButton]))
    self.layout().addStretch(1)

  def setupIntraopSeriesSelector(self):
    self.intraopSeriesSelector = qt.QComboBox()
    self.intraopSeriesSelector.setSizePolicy(qt.QSizePolicy.Expanding, qt.QSizePolicy.Minimum)
    self.intraopSeriesSelector.setMinimumContentsLength(20)
    self.intraopSeriesSelector.setSizeAdjustPolicy(qt.QComboBox().AdjustToMinimumContentsLength)
    self._seriesModel = qt.QStandardItemModel()
    self.intraopSeriesSelector.setModel(self._seriesModel)

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
    self.intraopSeriesSelector.setStyleSheet("QComboBox{'background-color: green;'} QToolTip{background-color: white;}")

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
      self.intraopSeriesSelector.setToolTip(callData)
      self.setupFourUpView(self.session.currentSeriesVolume)

  @logmethod(logging.INFO)
  def onZFrameRegistrationSuccessful(self, caller, event):
    self.active = True

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

  def onActivation(self):
    super(ProstateCryoAblationOverviewStep, self).onActivation()
    self.updateIntraopSeriesSelectorTable()

  def onSeriesTypeManuallyAssigned(self, caller, event):
    self.updateIntraopSeriesSelectorTable()

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
    self.intraopSeriesSelector.setStyleSheet("QComboBox{'background-color: green;'} QToolTip{background-color: white;}")
    if self.active and not self.session.isLoading():
      self.selectMostRecentEligibleSeries()

  def selectMostRecentEligibleSeries(self):
    seriesTypeManager = SeriesTypeManager()
    self.intraopSeriesSelector.blockSignals(True)
    self.intraopSeriesSelector.setCurrentIndex(-1)
    self.intraopSeriesSelector.blockSignals(False)
    index = -1
    for item in list(reversed(range(len(self.session.seriesList)))):
      series = self._seriesModel.item(item).text()
      if seriesTypeManager.isWorkableSeries(series):
        index = self.intraopSeriesSelector.findText(series)
        break
    rowCount = self.intraopSeriesSelector.model().rowCount()
    self.intraopSeriesSelector.setCurrentIndex(index if index != -1 else (rowCount-1 if rowCount else -1))