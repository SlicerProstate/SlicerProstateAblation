import logging
import os
import datetime
import qt
import vtk
import re
import slicer
from SlicerDevelopmentToolboxUtils.decorators import logmethod
from SlicerDevelopmentToolboxUtils.widgets import ExtendedQMessageBox

from constants import ProstateCryoAblationConstants as constants
from SlicerDevelopmentToolboxUtils.module.logic import LogicBase
from SlicerDevelopmentToolboxUtils.module.base import ModuleBase
from SlicerDevelopmentToolboxUtils.mixins import ModuleWidgetMixin
from SlicerDevelopmentToolboxUtils.metaclasses import Singleton
from SlicerDevelopmentToolboxUtils.icons import Icons

class NewCaseSelectionNameWidget(qt.QMessageBox, ModuleWidgetMixin):

  PREFIX = "Case"
  SUFFIX = "-" + datetime.date.today().strftime("%Y%m%d")
  SUFFIX_PATTERN = "-[0-9]{8}"
  CASE_NUMBER_DIGITS = 3
  PATTERN = PREFIX+"[0-9]{"+str(CASE_NUMBER_DIGITS-1)+"}[0-9]{1}"+SUFFIX_PATTERN

  def __init__(self, destination, parent=None):
    super(NewCaseSelectionNameWidget, self).__init__(parent)
    if not os.path.exists(destination):
      raise
    self.destinationRoot = destination
    self.newCaseDirectory = None
    self.minimum = self.getNextCaseNumber()
    self.setupUI()
    self.setupConnections()
    self.onCaseNumberChanged(self.minimum)

  def getNextCaseNumber(self):
    caseNumber = 0
    for dirName in [dirName for dirName in os.listdir(self.destinationRoot)
                     if os.path.isdir(os.path.join(self.destinationRoot, dirName)) and re.match(self.PATTERN, dirName)]:
      number = int(re.split(self.SUFFIX_PATTERN, dirName)[0].split(self.PREFIX)[1])
      caseNumber = caseNumber if caseNumber > number else number
    return caseNumber+1

  def setupUI(self):
    self.setWindowTitle("Case Number Selection")
    self.spinbox = qt.QSpinBox()
    self.spinbox.setRange(self.minimum, int("9"*self.CASE_NUMBER_DIGITS))

    self.hideInvisibleUnneededComponents()

    self.textLabel = qt.QLabel("Please select a case number for the new case.")
    self.textLabel.setStyleSheet("font-weight: bold;")
    self.previewLabel = qt.QLabel("New case directory:")
    self.preview = qt.QLabel()
    self.notice = qt.QLabel()
    self.notice.setStyleSheet("color:red;")

    self.okButton = self.addButton(self.Ok)
    self.okButton.enabled = False
    self.cancelButton = self.addButton(self.Cancel)
    self.setDefaultButton(self.okButton)

    self.groupBox = qt.QGroupBox()
    self.groupBox.setLayout(qt.QGridLayout())
    self.groupBox.layout().addWidget(self.textLabel, 0, 0, 1, 2)
    self.groupBox.layout().addWidget(qt.QLabel("Proposed Case Number"), 1, 0)
    self.groupBox.layout().addWidget(self.spinbox, 1, 1)
    self.groupBox.layout().addWidget(self.previewLabel, 2, 0, 1, 2)
    self.groupBox.layout().addWidget(self.preview, 3, 0, 1, 2)
    self.groupBox.layout().addWidget(self.notice, 4, 0, 1, 2)

    self.groupBox.layout().addWidget(self.okButton, 5, 0)
    self.groupBox.layout().addWidget(self.cancelButton, 5, 1)

    self.layout().addWidget(self.groupBox, 1, 1)

  def hideInvisibleUnneededComponents(self):
    for oName in ["qt_msgbox_label", "qt_msgboxex_icon_label"]:
      try:
        slicer.util.findChild(self, oName).hide()
      except RuntimeError:
        pass

  def setupConnections(self):
    self.spinbox.valueChanged.connect(self.onCaseNumberChanged)

  def onCaseNumberChanged(self, caseNumber):
    formatString = '%0'+str(self.CASE_NUMBER_DIGITS)+'d'
    caseNumber = formatString % caseNumber
    directory = self.PREFIX+caseNumber+self.SUFFIX
    self.newCaseDirectory = os.path.join(self.destinationRoot, directory)
    self.preview.setText( self.newCaseDirectory)
    self.okButton.enabled = not os.path.exists(self.newCaseDirectory)
    self.notice.text = "" if not os.path.exists(self.newCaseDirectory) else "Note: Directory already exists."


class SeriesTypeManager(LogicBase):

  SeriesTypeManuallyAssignedEvent = vtk.vtkCommand.UserEvent + 2334

  MODULE_NAME = constants.MODULE_NAME

  __metaclass__ = Singleton

  assignedSeries = {}

  def __init__(self):
    LogicBase.__init__(self)
    self.seriesTypes = self.getSetting("SERIES_TYPES")

  def clear(self):
    self.assignedSeries = {}

  def getSeriesType(self, series):
    try:
      return self.assignedSeries[series]
    except KeyError:
      return self.computeSeriesType(series)

  def checkInSetting(self, series, settingName):
    seriesType = None
    if type(self.getSetting(settingName)) is type(tuple()):
      for keyWord in self.getSetting(settingName):
        if keyWord in series:
          seriesType = keyWord
          break
    elif type(self.getSetting(settingName)) is type(unicode()):
      if self.getSetting(settingName) in series:
        seriesType = self.getSetting(settingName)
    return seriesType

  def computeSeriesType(self, series):
    seriesType = self.checkInSetting(series, "OTHER_IMAGE")
    if self.checkInSetting(series, "COVER_PROSTATE"):
      seriesType = self.checkInSetting(series, "COVER_PROSTATE")
    elif self.checkInSetting(series, "COVER_TEMPLATE"):
      seriesType = self.checkInSetting(series, "COVER_TEMPLATE")
    elif self.checkInSetting(series, "NEEDLE_IMAGE"):
      seriesType = self.checkInSetting(series, "NEEDLE_IMAGE")
    elif self.checkInSetting(series, "VIBE_IMAGE"):
      seriesType = self.checkInSetting(series, "VIBE_IMAGE")
    return seriesType

  def autoAssign(self, series):
    self.assignedSeries[series] = self.getSeriesType(series)

  def assign(self, series, seriesType=None):
    if series in self.assignedSeries.keys() and self.assignedSeries[series] == seriesType:
      return
    if seriesType:
      assert seriesType in self.seriesTypes
      self.assignedSeries[series] = seriesType
      self.invokeEvent(self.SeriesTypeManuallyAssignedEvent)
    else:
      self.autoAssign(series)

  def isCoverProstate(self, series):
    return self._hasSeriesType(series, self.getSetting("COVER_PROSTATE"))

  def isCoverTemplate(self, series):
    return self._hasSeriesType(series, self.getSetting("COVER_TEMPLATE"))

  def isGuidance(self, series):
    return self._hasSeriesType(series, self.getSetting("NEEDLE_IMAGE"))

  def isVibe(self, series):
    return self._hasSeriesType(series, self.getSetting("VIBE_IMAGE"))

  def isOther(self, series):
    return self._hasSeriesType(series, self.getSetting("OTHER_IMAGE")) or not (self.isCoverProstate(series) or
                                                                               self.isCoverTemplate(series) or
                                                                               self.isGuidance(series) or
                                                                               self.isVibe(series))
  def isWorkableSeries(self, series):
    return (self.isCoverProstate(series) or self.isCoverTemplate(series) or self.isGuidance(series) or self.isVibe(series))

  def _hasSeriesType(self, series, seriesType):
    listItems = [str(item) for item in seriesType]
    if self.assignedSeries.has_key(series):
      for serieName in listItems:
        if self.assignedSeries[series] == serieName:
          return True
    else:
      for serieName in listItems:
        if serieName in series:
          return True
    return False
