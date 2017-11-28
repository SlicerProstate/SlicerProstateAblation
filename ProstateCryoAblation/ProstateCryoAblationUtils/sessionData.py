import logging
import slicer, vtk
import os, json
import shutil
from collections import OrderedDict

from SlicerDevelopmentToolboxUtils.constants import FileExtension
from SlicerDevelopmentToolboxUtils.mixins import ModuleLogicMixin
from SlicerDevelopmentToolboxUtils.decorators import onExceptionReturnNone, logmethod
from SlicerDevelopmentToolboxUtils.widgets import CustomStatusProgressbar

from helpers import SeriesTypeManager


class SessionData(ModuleLogicMixin):

  NewResultCreatedEvent = vtk.vtkCommand.UserEvent + 901

  DEFAULT_JSON_FILE_NAME = "results.json"

  _completed = False
  _resumed = False

  @property
  def completed(self):
    return self._completed

  @completed.setter
  def completed(self, value):
    self._completed = value
    self.completedLogTimeStamp = self.generateLogfileTimeStampDict() if self._completed else None

  @property
  def resumed(self):
    return self._resumed

  @resumed.setter
  def resumed(self, value):
    if value and self.completed:
      raise ValueError("Completed case is not supposed to be resumed.")
    if value and not self.completed:
      self.resumeTimeStamps.append(self.getTime())
    self._resumed = value

  @staticmethod
  def wasSessionCompleted(filename):
    with open(filename) as data_file:
      data = json.load(data_file)
      procedureEvents = data["procedureEvents"]
      return "caseCompleted" in procedureEvents.keys()

  def __init__(self):
    self.resetAndInitializeData()

  def resetAndInitializeData(self):
    self.seriesTypeManager = SeriesTypeManager()
    self.startTimeStamp = self.getTime()
    self.resumeTimeStamps = []
    self.closedLogTimeStamps = []

    self.completed = False

    self.segmentModelNode = None

    self.initialVolume = None
    self.initialLabel = None
    self.initialTargets = None
    self.initialTargetsPath = None

    self.zFrameRegistrationResult = None

    self.customProgressBar = CustomStatusProgressbar()
    

  def createZFrameRegistrationResult(self, series):
    self.zFrameRegistrationResult = ZFrameRegistrationResult(series)
    return self.zFrameRegistrationResult

  def readProcedureEvents(self, procedureEvents):
    self.startTimeStamp = procedureEvents["caseStarted"]
    self.completed = "caseCompleted" in procedureEvents.keys()
    if self.completed:
      self.completedLogTimeStamp = procedureEvents["caseCompleted"]
    if "caseClosed" in procedureEvents.keys():
      self.closedLogTimeStamps = procedureEvents["caseClosed"]
    if "caseResumed" in procedureEvents.keys():
      self.resumeTimeStamps = procedureEvents["caseResumed"]

  def load(self, filename):
    directory = os.path.dirname(filename)
    self.resetAndInitializeData()
    self.alreadyLoadedFileNames = {}
    with open(filename) as data_file:
      self.customProgressBar.visible = True
      self.customProgressBar.text = "Reading meta information"
      logging.debug("reading json file %s" % filename)
      data = json.load(data_file)

      self.readProcedureEvents(data["procedureEvents"])

      if "initialTargets" in data.keys():
        self.initialTargets = self._loadOrGetFileData(directory,
                                                      data["initialTargets"], slicer.util.loadMarkupsFiducialList)
        self.initialTargetsPath = os.path.join(directory, data["initialTargets"])

      if "zFrameRegistration" in data.keys():
        zFrameRegistration = data["zFrameRegistration"]
        volume = self._loadOrGetFileData(directory, zFrameRegistration["volume"], slicer.util.loadVolume)
        transform = self._loadOrGetFileData(directory, zFrameRegistration["transform"], slicer.util.loadTransform)
        name = zFrameRegistration["name"] if zFrameRegistration.has_key("name") else volume.GetName()
        self.zFrameRegistrationResult = ZFrameRegistrationResult(name)
        self.zFrameRegistrationResult.volume = volume
        self.zFrameRegistrationResult.transform = transform
        if zFrameRegistration["seriesType"]:
          self.seriesTypeManager.assign(self.zFrameRegistrationResult.name, zFrameRegistration["seriesType"])

      if "initialVolume" in data.keys():
        self.initialVolume = self._loadOrGetFileData(directory, data["initialVolume"], slicer.util.loadVolume)

      if "tumorSegmentation" in data.keys():
        self.segmentModelNode = self._loadOrGetFileData(directory, data["tumorSegmentation"], slicer.util.loadSegmentation)

      #self.loadResults(data, directory) ## ?? why need to load twice
    return True

  def _loadOrGetFileData(self, directory, filename, loadFunction):
    if not filename:
      return None
    try:
      data = self.alreadyLoadedFileNames[filename]
    except KeyError:
      _, data = loadFunction(os.path.join(directory, filename), returnNode=True)
      self.alreadyLoadedFileNames[filename] = data
    return data

  def generateLogfileTimeStampDict(self):
    return {
      "time": self.getTime(),
      "logfile": os.path.basename(self.getSlicerErrorLogPath())
    }

  def close(self, outputDir):
    if not self.completed:
      self.closedLogTimeStamps.append(self.generateLogfileTimeStampDict())
    return self.save(outputDir)

  def save(self, outputDir):
    if not os.path.exists(outputDir):
      self.createDirectory(outputDir)

    successfullySavedFileNames = []
    failedSaveOfFileNames = []

    logFilePath = self.getSlicerErrorLogPath()
    shutil.copy(logFilePath, os.path.join(outputDir, os.path.basename(logFilePath)))
    successfullySavedFileNames.append(os.path.join(outputDir, os.path.basename(logFilePath)))

    def saveManualSegmentation():
      if self.segmentModelNode:
        if self.segmentModelNode.GetSegmentation().GetNumberOfSegments()>0:
          success, name = self.saveNodeData(self.segmentModelNode, outputDir, ".seg.nrrd", overwrite=True)
          self.handleSaveNodeDataReturn(success, name, successfullySavedFileNames, failedSaveOfFileNames)
          return name + ".seg.nrrd"
      return None

    def saveInitialTargets():
      success, name = self.saveNodeData(self.initialTargets, outputDir, FileExtension.FCSV,
                                        name="Initial_Targets", overwrite=True)
      self.handleSaveNodeDataReturn(success, name, successfullySavedFileNames, failedSaveOfFileNames)
      return name + FileExtension.FCSV

    def saveInitialVolume():
      success, name = self.saveNodeData(self.initialVolume, outputDir, FileExtension.NRRD, overwrite=True)
      self.handleSaveNodeDataReturn(success, name, successfullySavedFileNames, failedSaveOfFileNames)
      return name + FileExtension.NRRD

    data = {}

    def addProcedureEvents():
      procedureEvents = {
        "caseStarted": self.startTimeStamp,
      }
      if len(self.closedLogTimeStamps):
        procedureEvents["caseClosed"] = self.closedLogTimeStamps
      if len(self.resumeTimeStamps):
        procedureEvents["caseResumed"] = self.resumeTimeStamps
      if self.completed:
        procedureEvents["caseCompleted"] = self.completedLogTimeStamp
      data["procedureEvents"] = procedureEvents

    addProcedureEvents()

    if self.zFrameRegistrationResult:
      data["zFrameRegistration"] = self.zFrameRegistrationResult.save(outputDir)

    if self.initialTargets:
      data["initialTargets"] = saveInitialTargets()

    if self.initialVolume:
      data["initialVolume"] = saveInitialVolume()

    if self.segmentModelNode:
      data["tumorSegmentation"] = saveManualSegmentation()

    destinationFile = os.path.join(outputDir, self.DEFAULT_JSON_FILE_NAME)
    with open(destinationFile, 'w') as outfile:
      logging.debug("Writing registration results to %s" % destinationFile)
      json.dump(data, outfile, indent=2)

    self.printOutput("The following data was successfully saved:\n", successfullySavedFileNames)
    self.printOutput("The following data failed to saved:\n", failedSaveOfFileNames)
    return (len(failedSaveOfFileNames) == 0, failedSaveOfFileNames)
    
  def printOutput(self, message, fileNames):
    if not len(fileNames):
      return
    for fileName in fileNames:
      message += fileName + "\n"
    logging.debug(message)

class Transforms(object):

  FILE_EXTENSION = FileExtension.H5

  def __init__(self):
    super(Transforms, self).__init__()


class Targets(object):

  FILE_EXTENSION = FileExtension.FCSV

  def __init__(self):
    super(Targets, self).__init__()


class Volumes(object):

  FILE_EXTENSION = FileExtension.NRRD

  def __init__(self):
    super(Volumes, self).__init__()


class Labels(object):

  FILE_EXTENSION = FileExtension.NRRD

  def __init__(self):
    super(Labels, self).__init__()


class Segments(object):

  FILE_EXTENSION = ".seg.nrrd"

  def __init__(self):
    super(Segments, self).__init__()

class ZFrameRegistrationResult(ModuleLogicMixin):

  def __init__(self, series):
    self.name = series
    self.volume = None
    self.transform = None

  def save(self, outputDir):
    seriesTypeManager = SeriesTypeManager()
    dictionary = {
      "name": self.name,
      "seriesType": seriesTypeManager.getSeriesType(self.name)
    }
    savedSuccessfully = []
    failedToSave = []
    success, name = self.saveNodeData(self.transform, outputDir, FileExtension.H5, overwrite=True)
    dictionary["transform"] = name + FileExtension.H5
    self.handleSaveNodeDataReturn(success, name, savedSuccessfully, failedToSave)
    success, name = self.saveNodeData(self.volume, outputDir, FileExtension.NRRD, overwrite=True)
    dictionary["volume"] = name + FileExtension.NRRD
    self.handleSaveNodeDataReturn(success, name, savedSuccessfully, failedToSave)
    return dictionary