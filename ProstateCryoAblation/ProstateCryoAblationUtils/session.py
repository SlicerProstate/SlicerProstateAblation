import os, logging
import vtk, ctk, ast

import slicer
from sessionData import SessionData, RegistrationResult, RegistrationTypeData
from ProstateCryoAblationUtils.constants import ProstateCryoAblationConstants as constants
from helpers import SeriesTypeManager

from .exceptions import DICOMValueError, PreProcessedDataError, UnknownSeriesError

from SlicerDevelopmentToolboxUtils.constants import DICOMTAGS, FileExtension, STYLE
from SlicerDevelopmentToolboxUtils.events import SlicerDevelopmentToolboxEvents
from SlicerDevelopmentToolboxUtils.helpers import SmartDICOMReceiver
from SlicerDevelopmentToolboxUtils.mixins import ModuleWidgetMixin
from SlicerDevelopmentToolboxUtils.widgets import IncomingDataWindow, CustomStatusProgressbar
from SlicerDevelopmentToolboxUtils.decorators import logmethod, singleton
from SlicerDevelopmentToolboxUtils.decorators import onExceptionReturnFalse, onReturnProcessEvents, onExceptionReturnNone
from SlicerDevelopmentToolboxUtils.module.session import StepBasedSession


from SliceTrackerRegistration import SliceTrackerRegistrationLogic


@singleton
class ProstateCryoAblationSession(StepBasedSession):

  IncomingDataSkippedEvent = SlicerDevelopmentToolboxEvents.SkippedEvent
  IncomingPreopDataReceiveFinishedEvent = SlicerDevelopmentToolboxEvents.FinishedEvent + 110

  IncomingIntraopDataReceiveFinishedEvent = SlicerDevelopmentToolboxEvents.FinishedEvent + 111
  NewImageSeriesReceivedEvent = SlicerDevelopmentToolboxEvents.NewImageDataReceivedEvent

  DICOMReceiverStatusChanged = SlicerDevelopmentToolboxEvents.StatusChangedEvent
  DICOMReceiverStoppedEvent = SlicerDevelopmentToolboxEvents.StoppedEvent

  ZFrameRegistrationSuccessfulEvent = vtk.vtkCommand.UserEvent + 140
  PreprocessingSuccessfulEvent = vtk.vtkCommand.UserEvent + 141
  FailedPreprocessedEvent = vtk.vtkCommand.UserEvent + 142
  LoadingMetadataSuccessfulEvent = vtk.vtkCommand.UserEvent + 143
  SegmentationCancelledEvent = vtk.vtkCommand.UserEvent + 144

  CurrentSeriesChangedEvent = vtk.vtkCommand.UserEvent + 151
  RegistrationStatusChangedEvent = vtk.vtkCommand.UserEvent + 152

  InitiateZFrameCalibrationEvent = vtk.vtkCommand.UserEvent + 160
  InitiateTargetingEvent = vtk.vtkCommand.UserEvent + 161
  InitiateRegistrationEvent = vtk.vtkCommand.UserEvent + 162
  InitiateEvaluationEvent = vtk.vtkCommand.UserEvent + 163

  NeedleGuidanceEvent = vtk.vtkCommand.UserEvent + 164

  CurrentResultChangedEvent = vtk.vtkCommand.UserEvent + 234

  ApprovedEvent = RegistrationResult.ApprovedEvent
  SkippedEvent = RegistrationResult.SkippedEvent
  RejectedEvent = RegistrationResult.RejectedEvent

  SeriesTypeManuallyAssignedEvent = SeriesTypeManager.SeriesTypeManuallyAssignedEvent

  ResultEvents = [ApprovedEvent, SkippedEvent, RejectedEvent]

  MODULE_NAME = constants.MODULE_NAME

  @property
  def preprocessedDirectory(self):
    return os.path.join(self.directory, "Preprocessed") if self.directory else None

  @property
  def preopDICOMDirectory(self):
    return os.path.join(self.directory, "DICOM", "Preop") if self.directory else None

  @property
  def intraopDICOMDirectory(self):
    return os.path.join(self.directory, "DICOM", "Intraop") if self.directory else None

  @property
  def outputDirectory(self):
    # was outputDir
    return os.path.join(self.directory, "ProstateCryoAblationOutputs")

  @property
  def approvedCoverTemplate(self):
    try:
      return self.data.zFrameRegistrationResult.volume
    except AttributeError:
      return None

  @approvedCoverTemplate.setter
  def approvedCoverTemplate(self, volume):
    self.data.zFrameRegistrationResult.volume = volume
    self.zFrameRegistrationSuccessful = volume is not None

  @property
  def zFrameRegistrationSuccessful(self):
    self._zFrameRegistrationSuccessful = getattr(self, "_zFrameRegistrationSuccessful", None)
    return self.data.zFrameRegistrationResult is not None and self._zFrameRegistrationSuccessful

  @zFrameRegistrationSuccessful.setter
  def zFrameRegistrationSuccessful(self, value):
    self._zFrameRegistrationSuccessful = value
    if self._zFrameRegistrationSuccessful:
      self.save()
      self.invokeEvent(self.ZFrameRegistrationSuccessfulEvent)

  @property
  def currentResult(self):
    return self._getCurrentResult()

  @onExceptionReturnNone
  def _getCurrentResult(self):
    return self.data.registrationResults[self._currentResult]

  @currentResult.setter
  def currentResult(self, series):
    if self.currentResult and self.currentResult.name == series:
      return
    if self.currentResult is not None:
      self.currentResult.removeEventObservers()
    self._currentResult = series
    self.save()
    self.invokeEvent(self.CurrentResultChangedEvent)

  @property
  def currentSeries(self):
    self._currentSeries = getattr(self, "_currentSeries", None)
    return self._currentSeries

  @currentSeries.setter
  def currentSeries(self, series):
    if series == self.currentSeries:
      return
    print "set current Series on session"
    if series and series not in self.seriesList :
      raise UnknownSeriesError("Series %s is unknown" % series)
    self._currentSeries = series
    self.invokeEvent(self.CurrentSeriesChangedEvent, series)

  @property
  def currentSeriesVolume(self):
    if not self.currentSeries:
      return None
    else:
      return self.getOrCreateVolumeForSeries(self.currentSeries)

  @property
  def movingVolume(self):
    self._movingVolume = getattr(self, "_movingVolume", None)
    return self._movingVolume

  @movingVolume.setter
  def movingVolume(self, value):
    self._movingVolume = value

  @property
  def movingLabel(self):
    self._movingLabel = getattr(self, "_movingLabel", None)
    return self._movingLabel

  @movingLabel.setter
  def movingLabel(self, value):
    self._movingLabel = value

  @property
  def movingTargets(self):
    self._movingTargets = getattr(self, "_movingTargets", None)
    if self.isCurrentSeriesCoverProstateInNonPreopMode():
      return self.data.initialTargets
    return self._movingTargets

  @movingTargets.setter
  def movingTargets(self, value):
    if self.isCurrentSeriesCoverProstateInNonPreopMode():
      self.data.initialTargets = value
    self._movingTargets = value
    
  @property
  def fixedVolume(self):
    self._fixedVolume = getattr(self, "_fixedVolume", None)
    if self.isCurrentSeriesCoverProstateInNonPreopMode():
      return self.data.initialVolume
    return self._fixedVolume

  @fixedVolume.setter
  def fixedVolume(self, value):
    if self.isCurrentSeriesCoverProstateInNonPreopMode():
      self.data.initialVolume = value
    self._fixedVolume = value

  @property
  def fixedLabel(self):
    self._fixedLabel = getattr(self, "_fixedLabel", None)
    if self.isCurrentSeriesCoverProstateInNonPreopMode():
      return self.data.initialLabel
    return self._fixedLabel

  @fixedLabel.setter
  def fixedLabel(self, value):
    if self.isCurrentSeriesCoverProstateInNonPreopMode():
      self.data.initialLabel = value
    self._fixedLabel = value

  def __init__(self):
    StepBasedSession.__init__(self)
    self.registrationLogic = SliceTrackerRegistrationLogic()
    self.seriesTypeManager = SeriesTypeManager()
    self.seriesTypeManager.addEventObserver(self.seriesTypeManager.SeriesTypeManuallyAssignedEvent,
                                            lambda caller, event: self.invokeEvent(self.SeriesTypeManuallyAssignedEvent))

    self.resetAndInitializeMembers()
  
  def resetAndInitializeMembers(self):
    self.seriesTypeManager.clear()
    self.initializeColorNodes()
    self.directory = None
    self.data = SessionData()
    self.data.addEventObserver(self.data.NewResultCreatedEvent, self.onNewResultCreated)
    self.trainingMode = False
    self.resetPreopDICOMReceiver()
    self.resetIntraopDICOMReceiver()
    self.loadableList = {}
    self.seriesList = []
    self.alreadyLoadedSeries = {}
    self._currentResult = None
    self._currentSeries = None
    self.retryMode = False
    self.lastSelectedModelIndex = None
    self.previousStep = None

  def initializeColorNodes(self):
    from mpReview import mpReviewLogic
    self.mpReviewColorNode, self.structureNames = mpReviewLogic.loadColorTable(self.getSetting("Color_File_Name"))
    self.segmentedColorName = self.getSetting("Segmentation_Color_Name")
    self.segmentedLabelValue = self.mpReviewColorNode.GetColorIndexByName(self.segmentedColorName)
    
  def __del__(self):
    super(ProstateCryoAblationSession, self).__del__()
    self.clearData()

  def clearData(self):
    self.resetAndInitializeMembers()

  def onMrmlSceneCleared(self, caller, event):
    self.initializeColorNodes()
  
  @vtk.calldata_type(vtk.VTK_STRING)
  def onNewResultCreated(self, caller, event, callData):
    self.currentResult = callData  

  @onExceptionReturnFalse
  def isCurrentSeriesCoverProstateInNonPreopMode(self):
    return self.seriesTypeManager.isCoverProstate(self.currentSeries) and not self.data.usePreopData

  def isPreProcessing(self):
    return slicer.util.selectedModule() != self.MODULE_NAME

  def isCaseDirectoryValid(self):
    return os.path.exists(self.preopDICOMDirectory) and os.path.exists(self.intraopDICOMDirectory)

  def isRunning(self):
    return not self.directory in [None, '']

  def processDirectory(self):
    self.newCaseCreated = getattr(self, "newCaseCreated", False)
    if self.newCaseCreated:
      return
    if not self.directory or not self.isCaseDirectoryValid():
      slicer.util.warningDisplay("The selected case directory seems not to be valid", windowTitle="ProstateCryoAblation")
      self.close(save=False)
    else:
      self.loadCaseData()
      self.invokeEvent(self.CaseOpenedEvent)

  def createNewCase(self, destination):
    self.newCaseCreated = True
    self.resetAndInitializeMembers()
    self.directory = destination
    self.createDirectory(self.preopDICOMDirectory)
    self.createDirectory(self.intraopDICOMDirectory)
    self.createDirectory(self.preprocessedDirectory)
    self.createDirectory(self.outputDirectory)
    self.startPreopDICOMReceiver()
    self.newCaseCreated = False
    self.invokeEvent(self.NewCaseStartedEvent)

  def close(self, save=False):
    if not self.isRunning():
      return
    message = None
    if save:
      success, failedFileNames = self.data.close(self.outputDirectory)
      message = "Case data has been saved successfully." if success else \
        "The following data failed to saved:\n %s" % failedFileNames
    self.resetAndInitializeMembers()
    self.invokeEvent(self.CloseCaseEvent, str(message))

  def save(self):
    success, failedFileNames = self.data.save(self.outputDirectory)
    return success and not len(failedFileNames), "The following data failed to saved:\n %s" % failedFileNames

  def complete(self):
    self.data.completed = True
    self.close(save=True)

  def load(self):
    filename = os.path.join(self.outputDirectory, constants.JSON_FILENAME)
    completed = self.data.wasSessionCompleted(filename)
    if slicer.util.confirmYesNoDisplay("A %s session has been found for the selected case. Do you want to %s?" \
                                        % ("completed" if completed else "started",
                                           "open it" if completed else "continue this session")):
      slicer.app.layoutManager().blockSignals(True)
      self._loading = True
      self.data.load(filename)
      self.postProcessLoadedSessionData()
      self._loading = False
      slicer.app.layoutManager().blockSignals(False)
      self.invokeEvent(self.LoadingMetadataSuccessfulEvent)
    else:
      self.clearData()

  def postProcessLoadedSessionData(self):
    coverProstate = self.data.getMostRecentApprovedCoverProstateRegistration()
    if coverProstate:
      if not self.data.initialVolume:
        self.data.initialVolume = coverProstate.volumes.moving if self.data.usePreopData else coverProstate.volumes.fixed
      self.data.initialTargets = coverProstate.targets.original
      if self.data.usePreopData:  # TODO: makes sense?
        self.data.preopLabel = coverProstate.labels.moving
    if self.data.zFrameRegistrationResult:
      self._zFrameRegistrationSuccessful = True
    self.data.resumed = not self.data.completed
    if self.data.usePreopData:
      self.loadPreProcessedData()
    else:
      if self.data.initialTargets:
        self.setupPreopLoadedTargets()
      self.startIntraopDICOMReceiver()

  def startPreopDICOMReceiver(self):
    self.resetPreopDICOMReceiver()
    self.preopDICOMReceiver = IncomingDataWindow(incomingDataDirectory=self.preopDICOMDirectory,
                                                 skipText="No preoperative images available")
    self.preopDICOMReceiver.addEventObserver(SlicerDevelopmentToolboxEvents.SkippedEvent,
                                             self.onSkippingPreopDataReception)
    self.preopDICOMReceiver.addEventObserver(SlicerDevelopmentToolboxEvents.CanceledEvent,
                                             lambda caller, event: self.close())
    self.preopDICOMReceiver.addEventObserver(SlicerDevelopmentToolboxEvents.FinishedEvent,
                                             self.onPreopDataReceptionFinished)
    self.preopDICOMReceiver.show()

  def onSkippingPreopDataReception(self, caller, event):
    self.data.usePreopData = False
    self.startIntraopDICOMReceiver()
    self.invokeEvent(self.IncomingDataSkippedEvent)

  def onPreopDataReceptionFinished(self, caller, event):
    self.data.usePreopData = True
    self.startIntraopDICOMReceiver()
    self.invokeEvent(self.IncomingPreopDataReceiveFinishedEvent)

  def resetPreopDICOMReceiver(self):
    self.preopDICOMReceiver = getattr(self, "preopDICOMReceiver", None)
    if self.preopDICOMReceiver:
      self.preopDICOMReceiver.hide()
      self.preopDICOMReceiver.removeEventObservers()
      self.preopDICOMReceiver = None

  def startIntraopDICOMReceiver(self):
    self.resetPreopDICOMReceiver()
    logging.info("Starting DICOM Receiver for intra-procedural data")
    if not self.data.completed:
      self.resetIntraopDICOMReceiver()
      self.intraopDICOMReceiver = SmartDICOMReceiver(self.intraopDICOMDirectory)
      self._observeIntraopDICOMReceiverEvents()
      self.intraopDICOMReceiver.start(not (self.trainingMode or self.data.completed))
    else:
      self.invokeEvent(SlicerDevelopmentToolboxEvents.StoppedEvent)
    self.importDICOMSeries(self.getFileList(self.intraopDICOMDirectory))
    if self.intraopDICOMReceiver:
      self.intraopDICOMReceiver.forceStatusChangeEventUpdate()

  def resetIntraopDICOMReceiver(self):
    self.intraopDICOMReceiver = getattr(self, "intraopDICOMReceiver", None)
    if self.intraopDICOMReceiver:
      self.intraopDICOMReceiver.stop()
      self.intraopDICOMReceiver.removeEventObservers()

  def _observeIntraopDICOMReceiverEvents(self):
    self.intraopDICOMReceiver.addEventObserver(self.intraopDICOMReceiver.IncomingDataReceiveFinishedEvent,
                                               self.onDICOMSeriesReceived)
    self.intraopDICOMReceiver.addEventObserver(SlicerDevelopmentToolboxEvents.StatusChangedEvent,
                                               self.onDICOMReceiverStatusChanged)

  @vtk.calldata_type(vtk.VTK_STRING)
  def onDICOMReceiverStatusChanged(self, caller, event, callData):
    customStatusProgressBar = CustomStatusProgressbar()
    customStatusProgressBar.text = callData
    if "Waiting" in callData:
      customStatusProgressBar.busy = True

  @vtk.calldata_type(vtk.VTK_STRING)
  def onDICOMSeriesReceived(self, caller, event, callData):
    self.importDICOMSeries(ast.literal_eval(callData))
    if self.trainingMode is True:
      self.resetIntraopDICOMReceiver()

  def importDICOMSeries(self, newFileList):
    indexer = ctk.ctkDICOMIndexer()

    newSeries = []
    for currentIndex, currentFile in enumerate(newFileList, start=1):
      self.invokeEvent(SlicerDevelopmentToolboxEvents.NewFileIndexedEvent,
                       ["Indexing file %s" % currentFile, len(newFileList), currentIndex].__str__())
      slicer.app.processEvents()
      currentFile = os.path.join(self.intraopDICOMDirectory, currentFile)
      indexer.addFile(slicer.dicomDatabase, currentFile, None)
      series = self.makeSeriesNumberDescription(currentFile)
      if series not in self.seriesList:
        if not series.split(": ")[0] == '__TAG_NOT_IN_INSTANCE__':
          self.seriesList.append(series)
          newSeries.append(series)
          self.loadableList[series] = self.createLoadableFileListForSeries(series)
    self.seriesList = sorted(self.seriesList, key=lambda s: RegistrationResult.getSeriesNumberFromString(s))

    if len(newFileList):
      self.verifyPatientIDEquality(newFileList)
      self.invokeEvent(self.NewImageSeriesReceivedEvent, newSeries.__str__())

  def verifyPatientIDEquality(self, receivedFiles):
    seriesNumberPatientID = self.getAdditionalInformationForReceivedSeries(receivedFiles)
    dicomFileName = self.getPatientIDValidationSource()
    if not dicomFileName:
      return
    currentInfo = self.getPatientInformation(dicomFileName)
    currentID = currentInfo["PatientID"]
    patientName = currentInfo["PatientName"]
    for seriesNumber, receivedInfo in seriesNumberPatientID.iteritems():
      patientID = receivedInfo["PatientID"]
      if patientID is not None and patientID != currentID:
        m = 'WARNING:\n' \
            'Current case:\n' \
            '  Patient ID: {0}\n' \
            '  Patient Name: {1}\n' \
            'Received image\n' \
            '  Patient ID: {2}\n' \
            '  Patient Name : {3}\n\n' \
            'Do you want to keep this series? '.format(currentID, patientName, patientID, receivedInfo["PatientName"])
        if not slicer.util.confirmYesNoDisplay(m, title="Patient IDs Not Matching", windowTitle="ProstateCryoAblation"):
          self.deleteSeriesFromSeriesList(seriesNumber)

  def getPatientIDValidationSource(self):
    # TODO: For loading case purposes it would be nice to keep track which series were accepted
    if len(self.loadableList.keys()) > 1:
      keylist = self.loadableList.keys()
      keylist.sort(key=lambda x: RegistrationResult.getSeriesNumberFromString(x))
      return self.loadableList[keylist[0]][0]
    else:
      return None

  def getOrCreateVolumeForSeries(self, series):
    try:
      volume = self.alreadyLoadedSeries[series]
    except KeyError:
      logging.info("Need to load volume")
      files = self.loadableList[series]
      loadables = self.scalarVolumePlugin.examine([files])
      success, volume = slicer.util.loadVolume(files[0], returnNode=True)
      volume.SetName(loadables[0].name)
      self.alreadyLoadedSeries[series] = volume
    slicer.app.processEvents()
    return volume

  def createLoadableFileListForSeries(self, series):
    seriesNumber = RegistrationResult.getSeriesNumberFromString(series)
    loadableList = []
    for dcm in self.getFileList(self.intraopDICOMDirectory):
      currentFile = os.path.join(self.intraopDICOMDirectory, dcm)
      if not self.getDICOMValue(currentFile, DICOMTAGS.SERIES_NUMBER)  == '__TAG_NOT_IN_INSTANCE__':
        currentSeriesNumber = int(self.getDICOMValue(currentFile, DICOMTAGS.SERIES_NUMBER))
        if currentSeriesNumber and currentSeriesNumber == seriesNumber:
          loadableList.append(currentFile)
    return loadableList

  def deleteSeriesFromSeriesList(self, seriesNumber):
    for series in self.seriesList:
      currentSeriesNumber = RegistrationResult.getSeriesNumberFromString(series)
      if currentSeriesNumber == seriesNumber:
        self.seriesList.remove(series)
        for seriesFile in self.loadableList[series]:
          logging.debug("removing {} from filesystem".format(seriesFile))
          os.remove(seriesFile)
        del self.loadableList[series]

  def makeSeriesNumberDescription(self, dcmFile):
    seriesDescription = self.getDICOMValue(dcmFile, DICOMTAGS.SERIES_DESCRIPTION)
    seriesNumber = self.getDICOMValue(dcmFile, DICOMTAGS.SERIES_NUMBER)
    if not (seriesNumber and seriesDescription):
      raise DICOMValueError("Missing Attribute(s):\nFile: {}\nseriesNumber: {}\nseriesDescription: {}"
                            .format(dcmFile, seriesNumber, seriesDescription))
    return "{}: {}".format(seriesNumber, seriesDescription)

  def getAdditionalInformationForReceivedSeries(self, fileList):
    seriesNumberPatientID = {}
    for currentFile in [os.path.join(self.intraopDICOMDirectory, f) for f in fileList]:
      seriesNumber = int(self.getDICOMValue(currentFile, DICOMTAGS.SERIES_NUMBER))
      if seriesNumber not in seriesNumberPatientID.keys():
        seriesNumberPatientID[seriesNumber]= self.getPatientInformation(currentFile)
    return seriesNumberPatientID

  def getPatientInformation(self, currentFile):
    return {
      "PatientID": self.getDICOMValue(currentFile, DICOMTAGS.PATIENT_ID),
      "PatientName": self.getDICOMValue(currentFile, DICOMTAGS.PATIENT_NAME),
      "SeriesDescription": self.getDICOMValue(currentFile, DICOMTAGS.SERIES_DESCRIPTION)}

  def getSeriesForSubstring(self, substring):
    for series in reversed(self.seriesList):
      if substring in series:
        return series
    return None

  def loadPreProcessedData(self):
    try:
      self.loadPreopData(self.getFirstMpReviewPreprocessedStudy(self.preprocessedDirectory))
      self.startIntraopDICOMReceiver()
    except PreProcessedDataError:
      self.close(save=False)

  def loadCaseData(self):
    if not os.path.exists(os.path.join(self.outputDirectory, constants.JSON_FILENAME)):
      from mpReview import mpReviewLogic
      if mpReviewLogic.wasmpReviewPreprocessed(self.preprocessedDirectory):
        self.loadPreProcessedData()
      else:
        if len(os.listdir(self.preopDICOMDirectory)):
          self.startPreopDICOMReceiver()
        elif len(os.listdir(self.intraopDICOMDirectory)):
          self.data.usePreopData = False
          self.startIntraopDICOMReceiver()
        else:
          self.startPreopDICOMReceiver()
    else:
      self.openSavedSession()

  def openSavedSession(self):
    self.load()

  def setupPreopLoadedTargets(self):
    targets = self.data.initialTargets
    ModuleWidgetMixin.setFiducialNodeVisibility(targets, show=True)
    self.applyDefaultTargetDisplayNode(targets)
    self.markupsLogic.JumpSlicesToNthPointInMarkup(targets.GetID(), 0)
    # self.targetTable.selectRow(0)
    # self.updateDisplacementChartTargetSelectorTable()

  def applyDefaultTargetDisplayNode(self, targetNode, new=False):
    displayNode = None if new else targetNode.GetDisplayNode()
    modifiedDisplayNode = self.setupDisplayNode(displayNode, True)
    targetNode.SetAndObserveDisplayNodeID(modifiedDisplayNode.GetID())

  def setupDisplayNode(self, displayNode=None, starBurst=False):
    if not displayNode:
      displayNode = slicer.vtkMRMLMarkupsDisplayNode()
      slicer.mrmlScene.AddNode(displayNode)
    displayNode.SetTextScale(0)
    displayNode.SetGlyphScale(2.5)
    if starBurst:
      displayNode.SetGlyphType(slicer.vtkMRMLAnnotationPointDisplayNode.StarBurst2D)
    return displayNode

  def getFirstMpReviewPreprocessedStudy(self, directory):
    # TODO add check here and selected the one which has targets in it
    # TODO: if several studies are available provide a drop down or anything similar for choosing
    directoryNames = [x[0] for x in os.walk(directory)]
    assert len(directoryNames) > 1
    return directoryNames[1]

  def loadPreopData(self, directory):
    message = self.loadMpReviewProcessedData(directory)
    logging.info(message)
    if message or not self.loadT2Label() or not self.loadPreopVolume() or not self.loadPreopTargets():
      self.invokeEvent(self.FailedPreprocessedEvent,
                       "Loading preop data failed.\nMake sure that the correct mpReview directory structure is used."
                       "\n\n Application expects a T2 volume, WholeGland segmentation and target(s). Do you want to "
                       "open/revisit pre-processing for the current case?")
    else:
      self.data.usePreopData = True
      self.setupPreopLoadedTargets()
      self.invokeEvent(self.PreprocessingSuccessfulEvent)
      # self.logic.preopLabel.GetDisplayNode().SetAndObserveColorNodeID(self.mpReviewColorNode.GetID())

  def loadMpReviewProcessedData(self, directory):
    from mpReview import mpReviewLogic
    resourcesDir = os.path.join(directory, 'RESOURCES')
    logging.debug(resourcesDir)
    if not os.path.exists(resourcesDir):
      message = "The selected directory does not fit the mpReview directory structure. Make sure that you select the " \
                "study root directory which includes directories RESOURCES"
      return message

    # self.progress = self.createProgressDialog(maximum=len(os.listdir(resourcesDir)))
    # seriesMap, metaFile = mpReviewLogic.loadMpReviewProcessedData(resourcesDir,
    #                                                               updateProgressCallback=self.updateProgressBar)
    seriesMap, metaFile = mpReviewLogic.loadMpReviewProcessedData(resourcesDir)
    # self.progress.delete()

    self.data.initialTargetsPath = os.path.join(directory, 'Targets')

    self.loadPreopImageAndLabel(seriesMap)

    if self.preopSegmentationPath is None:
      message = "No segmentations found.\nMake sure that you used mpReview for segmenting the prostate first and using " \
                "its output as the preop data input here."
      return message
    return None

  def loadPreopImageAndLabel(self, seriesMap):
    self.preopImagePath = None
    self.preopSegmentationPath = None
    segmentedColorName = self.getSetting("Segmentation_Color_Name")

    for series in seriesMap:
      seriesName = str(seriesMap[series]['LongName'])
      logging.debug('series Number ' + series + ' ' + seriesName)

      imagePath = os.path.join(seriesMap[series]['NRRDLocation'])
      segmentationPath = os.path.dirname(os.path.dirname(imagePath))
      segmentationPath = os.path.join(segmentationPath, 'Segmentations')

      if not os.path.exists(segmentationPath):
        continue
      else:
        if any(segmentedColorName in name for name in os.listdir(segmentationPath)):
          logging.debug(' FOUND THE SERIES OF INTEREST, ITS ' + seriesName)
          logging.debug(' LOCATION OF VOLUME : ' + str(seriesMap[series]['NRRDLocation']))
          logging.debug(' LOCATION OF IMAGE path : ' + str(imagePath))

          logging.debug(' LOCATION OF SEGMENTATION path : ' + segmentationPath)

          self.preopImagePath = seriesMap[series]['NRRDLocation']
          self.preopSegmentationPath = segmentationPath
          break

  def loadT2Label(self):
    if self.data.initialLabel:
      return True
    mostRecentFilename = self.getMostRecentWholeGlandSegmentation(self.preopSegmentationPath)
    success = False
    if mostRecentFilename:
      filename = os.path.join(self.preopSegmentationPath, mostRecentFilename)
      success, self.data.initialLabel = slicer.util.loadLabelVolume(filename, returnNode=True)
      if success:
        self.data.initialLabel.SetName('t2-label')
    return success

  def loadPreopVolume(self):
    if self.data.initialVolume:
      return True
    success, self.data.initialVolume = slicer.util.loadVolume(self.preopImagePath, returnNode=True)
    if success:
      self.data.initialVolume.SetName('VOLUME-PREOP')
    return success

  def loadPreopTargets(self):
    if self.data.initialTargets:
      return True
    if not os.path.exists(self.data.initialTargetsPath):
      return False
    mostRecentTargets = self.getMostRecentTargetsFile(self.data.initialTargetsPath)
    success = False
    if mostRecentTargets:
      filename = os.path.join(self.data.initialTargetsPath, mostRecentTargets)
      success, self.data.initialTargets = slicer.util.loadMarkupsFiducialList(filename, returnNode=True)
      if success:
        self.data.initialTargets.SetName('targets-PREOP')
        self.data.initialTargets.SetLocked(True)
    return success

  def getMostRecentWholeGlandSegmentation(self, path):
    return self.getMostRecentFile(path, FileExtension.NRRD, filter="WholeGland")

  def getMostRecentTargetsFile(self, path):
    return self.getMostRecentFile(path, FileExtension.FCSV)

  def getColorForSelectedSeries(self, series=None):
    series = series if series else self.currentSeries
    if series in [None, '']:
      return STYLE.WHITE_BACKGROUND
    style = STYLE.YELLOW_BACKGROUND
    if not self.isTrackingPossible(series):
      if self.data.registrationResultWasApproved(series) or \
              (self.zFrameRegistrationSuccessful and self.seriesTypeManager.isCoverTemplate(series)):
        style = STYLE.GREEN_BACKGROUND
      elif self.data.registrationResultWasSkipped(series):
        style = STYLE.RED_BACKGROUND
      elif self.data.registrationResultWasRejected(series):
        style = STYLE.GRAY_BACKGROUND
    return style

  def isTrackingPossible(self, series):
    if self.data.completed:
      logging.debug("No tracking possible. Case has been marked as completed!")
      return False
    else:
      return True

  def isEligibleForSkipping(self, series):
    seriesType = self.seriesTypeManager.getSeriesType(series)
    return not self.isAnyListItemInString(seriesType,[self.getSetting("COVER_PROSTATE"), self.getSetting("COVER_TEMPLATE")])

  def isLoading(self):
    self._loading = getattr(self, "_loading", False)
    return self._loading

  def takeActionForCurrentSeries(self):
    event = None
    callData = None
    if self.seriesTypeManager.isCoverProstate(self.currentSeries):
      event = self.InitiateTargetingEvent
      callData = str(False)
    elif self.seriesTypeManager.isCoverTemplate(self.currentSeries):
      event = self.InitiateZFrameCalibrationEvent
    elif self.seriesTypeManager.isGuidance(self.currentSeries):
      event = self.NeedleGuidanceEvent
    if event:
      self.invokeEvent(event, callData)
    else:
      raise UnknownSeriesError("Action for currently selected series unknown")
  
  def generateNameAndCreateRegistrationResult(self, fixedVolume):
    result = self.data.createResult(fixedVolume.GetName())
    #self.registrationLogic.registrationResult = result
    return result  

  @onReturnProcessEvents
  def updateProgressBar(self, **kwargs):
    if self.progress:
      for key, value in kwargs.iteritems():
        if hasattr(self.progress, key):
          setattr(self.progress, key, value)

  
  def addTargetsToMrmlScene(self, result):
    targetNodes = result.targets.asDict()
    for regType in RegistrationTypeData.RegistrationTypes:
      if targetNodes[regType]:
        slicer.mrmlScene.AddNode(targetNodes[regType])

  def skipSeries(self, series):
    volume = self.getOrCreateVolumeForSeries(series)
    name, suffix = self.getRegistrationResultNameAndGeneratedSuffix(volume.GetName())
    result = self.data.createResult(name+suffix)
    result.volumes.fixed = volume
    result.skip()

  def skip(self, series):
    self.skipSeries(series)
    self.save()