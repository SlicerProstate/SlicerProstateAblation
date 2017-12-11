import qt
import vtk
import numpy
import logging
import slicer
from ...constants import ProstateCryoAblationConstants as constants
from ..base import ProstateCryoAblationPlugin, ProstateCryoAblationLogicBase
from ProstateCryoAblationUtils.steps.zFrameRegistration import ProstateCryoAblationZFrameRegistrationStepLogic
from SlicerDevelopmentToolboxUtils.mixins import ModuleLogicMixin
from SlicerDevelopmentToolboxUtils.decorators import onModuleSelected
from SlicerDevelopmentToolboxUtils.helpers import SliceAnnotation
from functools import partial


class MyCheckBox(qt.QWidget):
  def __init__(self, parent=None):
    qt.QWidget.__init__(self, parent)
    # create a centered checkbox
    self.cb = qt.QCheckBox(parent)
    cbLayout = qt.QHBoxLayout()
    self.cb.setSizePolicy(qt.QSizePolicy.Preferred, qt.QSizePolicy.Preferred)
    cbLayout.addWidget(self.cb, 0, qt.Qt.AlignCenter)
    self.setLayout(cbLayout)
    self.cb.toggled.connect(self.amClicked)

  def amClicked(self):
    self.cb.clicked.emit()

  def setChecked(self, check):
    self.cb.setChecked(check)

  def isChecked(self):
    return self.cb.isChecked()

class CheckBoxDelegate(qt.QItemDelegate):
  """
  A delegate that places a fully functioning QCheckBox in every
  cell of the column to which it's applied
  """

  def __init__(self, parent, prostateCryoAblationSession):
    qt.QItemDelegate.__init__(self, parent)
    self.session = prostateCryoAblationSession

  def createEditor(self, painDevice, option, index):
    if not (qt.Qt.ItemIsEditable & index.flags()):
      return None
    rowNum = index.row()
    targetNode = self.session.targetingPlugin.targetTablePlugin.currentTargets
    checked = self.session.displayForTargets.get(targetNode.GetNthMarkupID(rowNum))
    if checked is None:
      self.session.displayForTargets[targetNode.GetNthMarkupID(rowNum)] = qt.Qt.Unchecked
      checked = qt.Qt.Unchecked
    customCheckbox = MyCheckBox(painDevice)
    if not (self.parent().checkBoxList is None):
      self.parent().checkBoxList[targetNode.GetNthMarkupID(rowNum)] = customCheckbox
    customCheckbox.cb.setChecked(checked)
    self.connect(customCheckbox.cb, qt.SIGNAL("clicked()"), partial(self.clicked, customCheckbox))
    return customCheckbox

  def setModelData(self, checkbox, model, index):
    # Send data to the model
    rowNum = index.row()
    targetNode = self.session.targetingPlugin.targetTablePlugin.currentTargets
    self.session.displayForTargets[targetNode.GetNthMarkupID(rowNum)] = qt.Qt.Checked if checkbox.isChecked() else qt.Qt.Unchecked
    model.setData(index, checkbox.isChecked(), qt.Qt.EditRole)
    self.session.updateAffectiveZone()

  def clicked(self, checkbox):
    self.commitData.emit(checkbox)


class ComBoxDelegate(qt.QItemDelegate):
  """
  A delegate that places a fully functioning QCheckBox in every
  cell of the column to which it's applied
  """

  def __init__(self, parent, prostateCryoAblationSession):
    qt.QItemDelegate.__init__(self, parent)
    self.session = prostateCryoAblationSession

  def createEditor(self, painDevice, option, index):
    if not (qt.Qt.ItemIsEditable & index.flags()):
      return None
    rowNum = index.row()
    targetNode = self.session.targetingPlugin.targetTablePlugin.currentTargets
    needleType = self.session.needleTypeForTargets.get(targetNode.GetNthMarkupID(rowNum))
    if needleType is None:
      self.session.needleTypeForTargets[targetNode.GetNthMarkupID(rowNum)] = self.session.ISSEEDTYPE
      needleType =  self.session.ISSEEDTYPE
    comboBox = qt.QComboBox(painDevice)
    comboBoxItems = []
    comboBoxItems.append(self.session.ISSEEDTYPE)
    comboBoxItems.append(self.session.ISRODTYPE)
    comboBox.addItems(comboBoxItems)
    comboBox.setCurrentIndex(0)
    if not (self.parent().comboBoxList is None):
      self.parent().comboBoxList[targetNode.GetNthMarkupID(rowNum)] = comboBox
    self.connect(comboBox, qt.SIGNAL("currentIndexChanged(int)"), partial(self.currentIndexChanged, comboBox))
    return comboBox

  def setModelData(self, comboBox, model, index):
    # Send data to the model
    rowNum = index.row()
    targetNode = self.session.targetingPlugin.targetTablePlugin.currentTargets
    storedIndex = comboBox.findText(self.session.needleTypeForTargets[targetNode.GetNthMarkupID(rowNum)])
    if not storedIndex == comboBox.currentIndex:
      if slicer.util.confirmYesNoDisplay("Do you really want to Change the needle type? ", title="Needle Type Select",
                                         windowTitle="ProstateCryoAblation"):

        self.session.needleTypeForTargets[targetNode.GetNthMarkupID(rowNum)] = comboBox.currentText
        model.setData(index, comboBox.currentText, qt.Qt.EditRole)
        self.session.updateAffectiveZone()
      else:
        storedIndex =  comboBox.findText(self.session.needleTypeForTargets[targetNode.GetNthMarkupID(rowNum)])
        comboBox.blockSignals(True)
        comboBox.setCurrentIndex(storedIndex)
        comboBox.blockSignals(False)

  def currentIndexChanged(self, comboBox, int):
    print int, comboBox.currentText
    self.commitData.emit(comboBox)


class CustomTargetTableModel(qt.QAbstractTableModel, ModuleLogicMixin):

  PLANNING_IMAGE_NAME = "Initial registration"

  COLUMN_NAME = 'Name'
  COLUMN_DISPLAY = 'Display'
  COLUMN_NEEDLETYPE = 'NeedleType'
  COLUMN_HOLE = 'Hole'
  COLUMN_DEPTH = 'Depth[cm]'

  headers = [COLUMN_NAME, COLUMN_DISPLAY, COLUMN_NEEDLETYPE, COLUMN_HOLE, COLUMN_DEPTH]

  @property
  def targetList(self):
    return self._targetList

  @targetList.setter
  def targetList(self, targetList):
    self._targetList = targetList
    if self.currentGuidanceComputation and self.observer:
      self.currentGuidanceComputation.RemoveObserver(self.observer)
    self.currentGuidanceComputation = self.getOrCreateNewGuidanceComputation(targetList)
    if self.currentGuidanceComputation:
      self.observer = self.currentGuidanceComputation.addEventObserver(vtk.vtkCommand.ModifiedEvent,
                                                                       self.updateTable)
    self.reset()

  @property
  def coverProstateTargetList(self):
    self._coverProstateTargetList = getattr(self, "_coverProstateTargetList", None)
    return self._coverProstateTargetList

  @coverProstateTargetList.setter
  def coverProstateTargetList(self, targetList):
    self._coverProstateTargetList = targetList

  @property
  def cursorPosition(self):
    return self._cursorPosition

  @cursorPosition.setter
  def cursorPosition(self, cursorPosition):
    self._cursorPosition = cursorPosition
    self.dataChanged(self.index(0, 1), self.index(self.rowCount()-1, 2))

  def __init__(self, prostateCryoAblationSession, targets=None, parent=None, *args):
    qt.QAbstractTableModel.__init__(self, parent, *args)
    self.session = prostateCryoAblationSession
    self._cursorPosition = None
    self._targetList = None
    self._guidanceComputations = []
    self.currentGuidanceComputation = None
    self.targetList = targets
    self.computeCursorDistances = False
    self.currentTargetIndex = -1
    self.observer = None
    self.session.addEventObserver(self.session.ZFrameRegistrationSuccessfulEvent, self.onZFrameRegistrationSuccessful)
  
  def flags(self, index):
    if index.column() == self.getColunmNumForHeaderName(self.COLUMN_DISPLAY) \
        or index.column() == self.getColunmNumForHeaderName(self.COLUMN_NEEDLETYPE):
      return qt.Qt.ItemIsEnabled | qt.Qt.ItemIsEditable
    else:
      return qt.Qt.ItemIsEnabled
  
  def headerData(self, col, orientation, role):
    if orientation == qt.Qt.Horizontal and role in [qt.Qt.DisplayRole, qt.Qt.ToolTipRole]:
      return self.headers[col]
    return None

  def getColunmNumForHeaderName(self, headerName):
    for col, name in enumerate(self.headers):
      if headerName == name:
        return col
    return -1

  def getOrCreateNewGuidanceComputation(self, targetList):
    if not targetList:
      return None
    guidance = None
    for crntGuidance in self._guidanceComputations:
      if crntGuidance.targetList is targetList:
        guidance = crntGuidance
        break
    if not guidance:
      self._guidanceComputations.append(ZFrameGuidanceComputation(self.session, targetList))
      guidance = self._guidanceComputations[-1]
    if self._targetList is targetList:
      self.updateTable()
    return guidance

  def onZFrameRegistrationSuccessful(self, caller, event):
    self._guidanceComputations = []

  def updateTable(self, caller=None, event=None):
    self.dataChanged(self.index(0, self.getColunmNumForHeaderName(self.COLUMN_HOLE)), self.index(self.rowCount() - 1, self.getColunmNumForHeaderName(self.COLUMN_DEPTH)))
    self.invokeEvent(vtk.vtkCommand.ModifiedEvent)

  def rowCount(self):
    try:
      number_of_targets = self.targetList.GetNumberOfFiducials()
      return number_of_targets
    except AttributeError:
      return 0

  def columnCount(self):
    return len(self.headers)

  def data(self, index, role):
    result = self.getBackgroundOrToolTipData(index, role)
    if result:
      return result

    row = index.row()
    col = index.column()

    if not index.isValid() or role not in [qt.Qt.DisplayRole, qt.Qt.ToolTipRole]:
      return None


    if col == 0:
      return self.targetList.GetNthFiducialLabel(row)
    elif col == self.getColunmNumForHeaderName(self.COLUMN_DISPLAY):
      return None
    elif col == self.getColunmNumForHeaderName(self.COLUMN_NEEDLETYPE):
      return None
    elif col == 3 and self.session.zFrameRegistrationSuccessful:
      return self.currentGuidanceComputation.getZFrameHole(row)
    elif col == 4 and self.session.zFrameRegistrationSuccessful:
      return self.currentGuidanceComputation.getZFrameDepth(row)
    return ""

  def getBackgroundOrToolTipData(self, index, role):
    if role not in [qt.Qt.BackgroundRole, qt.Qt.ToolTipRole]:
      return None
    if self.currentGuidanceComputation is None:
      return None
    backgroundRequested = role == qt.Qt.BackgroundRole
    row = index.row()
    col = index.column()
    outOfRangeText = "" if self.currentGuidanceComputation.getZFrameDepthInRange(row) else "Current depth: out of range"
    if self.coverProstateTargetList and not self.coverProstateTargetList is self.targetList:
      if col in [3, 4]:
        coverProstateGuidance = self.getOrCreateNewGuidanceComputation(self.coverProstateTargetList)
        if col == 3:
          coverProstateHole = coverProstateGuidance.getZFrameHole(row)
          if self.currentGuidanceComputation.getZFrameHole(row) == coverProstateHole:
            return qt.QColor(qt.Qt.green) if backgroundRequested else ""
          else:
            return qt.QColor(qt.Qt.red) if backgroundRequested else "{} hole: {}".format(self.PLANNING_IMAGE_NAME,
                                                                                         coverProstateHole)
        elif col == 4:
          currentDepth = self.currentGuidanceComputation.getZFrameDepth(row, asString=False)
          coverProstateDepth = coverProstateGuidance.getZFrameDepth(row, asString=False)
          if abs(currentDepth - coverProstateDepth) <= max(1e-9 * max(abs(currentDepth), abs(coverProstateDepth)), 0.5):
            if backgroundRequested:
              return qt.QColor(qt.Qt.red) if len(outOfRangeText) else qt.QColor(qt.Qt.green)
            return "%s depth: '%.1f' %s" % (self.PLANNING_IMAGE_NAME, coverProstateDepth, "\n"+outOfRangeText)
          else:
            if backgroundRequested:
              return qt.QColor(qt.Qt.red)
            return "%s depth: '%.1f' %s" % (self.PLANNING_IMAGE_NAME, coverProstateDepth, "\n"+outOfRangeText)
    elif self.coverProstateTargetList is self.targetList and col == 4:
      if backgroundRequested and len(outOfRangeText):
        return qt.QColor(qt.Qt.red)
      elif len(outOfRangeText):
        return outOfRangeText
    return None


class ZFrameGuidanceComputation(ModuleLogicMixin):

  SUPPORTED_EVENTS = [vtk.vtkCommand.ModifiedEvent]

  def __init__(self, prostateCryoAblationSession, targetList = None):
    self.zFrameRegistration = ProstateCryoAblationZFrameRegistrationStepLogic(prostateCryoAblationSession)
    self.session = prostateCryoAblationSession
    self.targetList = targetList
    if self.targetList:
      self.observer = self.targetList.AddObserver(self.targetList.PointModifiedEvent, self.calculate)
      self.observer = self.targetList.AddObserver(self.targetList.MarkupRemovedEvent, self.calculate)
    self.reset()
    self.calculate()

  def __del__(self):
    if self.targetList and self.observer:
      self.targetList.RemoveObserver(self.observer)

  def reset(self):
    self.needleStartEndPositions = {}
    self.computedHoles = {}
    self.computedDepth = {}

  def calculate(self, caller=None, event=None):
    if not self.targetList:
      return
    self.reset()
    for index in range(self.targetList.GetNumberOfFiducials()):
      self.calculateZFrameHoleAndDepth(index)
    self.invokeEvent(vtk.vtkCommand.ModifiedEvent)

  def getNeedleEndPos(self, index):
    if index not in self.computedHoles.keys():
      self.calculateZFrameHoleAndDepth(index)
    return self.needleStartEndPositions[index][1]

  def getZFrameHole(self, index):
    if index not in self.computedHoles.keys():
      self.calculateZFrameHoleAndDepth(index)
    return '(%s, %s)' % (self.computedHoles[index][0], self.computedHoles[index][1])

  def getZFrameDepth(self, index, asString=True):
    if index not in self.computedHoles.keys():
      self.calculateZFrameHoleAndDepth(index)
    if asString:
      return '%.1f' % self.computedDepth[index][1] if self.computedDepth[index][0] else \
        '(%.1f)' % self.computedDepth[index][1]
    else:
      return self.computedDepth[index][1]

  def getZFrameDepthInRange(self, index):
    if index not in self.computedHoles.keys():
      self.calculateZFrameHoleAndDepth(index)
    return self.computedDepth[index][0]

  def calculateZFrameHoleAndDepth(self, index):
    targetPosition = self.getTargetPosition(self.targetList, index)
    (start, end, indexX, indexY, depth, inRange) = self.computeNearestPath(targetPosition)
    logging.debug("start:{}, end:{}, indexX:{}, indexY:{}, depth:{}, inRange:{}".format(start, end, indexX, indexY, depth, inRange))
    needleDirection = (numpy.array(end) - numpy.array(start)) / numpy.linalg.norm(numpy.array(end) - numpy.array(start))
    self.needleStartEndPositions[index] = (start, start + depth * needleDirection)
    self.computedHoles[index] = [indexX, indexY]
    self.computedDepth[index] = [inRange, round(depth/10, 1)]

  def computeNearestPath(self, pos):
    minMag2 = numpy.Inf
    minDepth = 0.0
    minIndex = -1
    needleStart = None
    needleEnd = None

    p = numpy.array(pos)
    for i, orig in enumerate(self.zFrameRegistration.pathOrigins):
      vec = self.zFrameRegistration.pathVectors[i]
      op = p - orig
      aproj = numpy.inner(op, vec)
      perp = op-aproj*vec
      mag2 = numpy.vdot(perp, perp)
      if mag2 < minMag2:
        minMag2 = mag2
        minIndex = i
        minDepth = aproj
      i += 1

    indexX = '--'
    indexY = '--'
    inRange = False

    if minIndex != -1:
      indexX = self.zFrameRegistration.templateIndex[minIndex][0]
      indexY = self.zFrameRegistration.templateIndex[minIndex][1]
      if 0 < minDepth < self.zFrameRegistration.templateMaxDepth[minIndex]:
        inRange = True
        needleStart, needleEnd = self.getNeedleStartEndPointFromPathOrigins(minIndex)

    return needleStart, needleEnd, indexX, indexY, minDepth, inRange

  def getNeedleStartEndPointFromPathOrigins(self, index):
    start = self.zFrameRegistration.pathOrigins[index]
    v = self.zFrameRegistration.pathVectors[index]
    nl = numpy.linalg.norm(v)
    n = v / nl  # normal vector
    l = self.zFrameRegistration.templateMaxDepth[index]
    end = start + l * n
    return start, end


class TargetsDefinitionTableLogic(ProstateCryoAblationLogicBase):

  def __init__(self, prostateCryoAblationSession):
    super(TargetsDefinitionTableLogic, self).__init__(prostateCryoAblationSession)

  def setTargetSelected(self, targetNode, selected=False):
    self.markupsLogic.SetAllMarkupsSelected(targetNode, selected)


class TargetsDefinitionTable(ProstateCryoAblationPlugin):

  NAME = "TargetTable"
  LogicClass = TargetsDefinitionTableLogic

  TargetPosUpdatedEvent = vtk.vtkCommand.UserEvent + 337

  @property
  def lastSelectedModelIndex(self):
    return self.session.lastSelectedModelIndex

  @lastSelectedModelIndex.setter
  def lastSelectedModelIndex(self, modelIndex):
    assert self.currentTargets is not None
    self.session.lastSelectedModelIndex = modelIndex

  @property
  def movingEnabled(self):
    self._movingEnabled = getattr(self, "_movingEnabled", False)
    return self._movingEnabled

  @movingEnabled.setter
  def movingEnabled(self, value):
    if self.movingEnabled  == value:
      return
    self._movingEnabled = value
    if self.movingEnabled:
      self.targetTable.connect('doubleClicked(QModelIndex)', self.onMoveTargetRequest)
    else:
      self.targetTable.disconnect('doubleClicked(QModelIndex)', self.onMoveTargetRequest)

  @property
  def currentTargets(self):
    self._currentTargets = getattr(self, "_currentTargets", None)
    return self._currentTargets

  @currentTargets.setter
  def currentTargets(self, targets):
    self.disableTargetMovingMode()
    self._currentTargets = targets
    self.targetTableModel.targetList = targets
    if not targets:
      self.targetTableModel.coverProstateTargetList = None
    self.targetTable.enabled = targets is not None
    for row in range(0, self.targetTableModel.rowCount()):
      self.targetTable.openPersistentEditor(self.targetTableModel.index(row, self.displayCol))
      self.targetTable.openPersistentEditor(self.targetTableModel.index(row, self.needleTypeCol))
      storedIndex = self.comboBoxList[self.currentTargets.GetNthMarkupID(row)].findText(self.session.needleTypeForTargets[self.currentTargets.GetNthMarkupID(row)])
      self.comboBoxList[self.currentTargets.GetNthMarkupID(row)].setCurrentIndex(storedIndex)
    if self.currentTargets:
      self.onTargetSelectionChanged()

  def __init__(self, prostateCryoAblationSession, **kwargs):
    super(TargetsDefinitionTable, self).__init__(prostateCryoAblationSession)
    self.movingEnabled = kwargs.pop("movingEnabled", False)
    self.checkBoxList = dict()
    self.comboBoxList = dict()
    self.keyPressEventObservers = {}
    self.keyReleaseEventObservers = {}
    self.mouseReleaseEventObservers = {}

  def setup(self):
    super(TargetsDefinitionTable, self).setup()
    self.targetTable = qt.QTableView()
    self.targetTableModel = CustomTargetTableModel(self.session)
    self.targetTable.setModel(self.targetTableModel)
    self.displayCol = self.targetTableModel.getColunmNumForHeaderName(self.targetTableModel.COLUMN_DISPLAY)
    self.needleTypeCol = self.targetTableModel.getColunmNumForHeaderName(self.targetTableModel.COLUMN_NEEDLETYPE)
    self.targetTable.setItemDelegateForColumn(self.displayCol, CheckBoxDelegate(self, self.session))
    self.targetTable.setItemDelegateForColumn(self.needleTypeCol, ComBoxDelegate(self, self.session))
    self.setTargetTableSizeConstraints()
    self.targetTable.verticalHeader().hide()
    self.targetTable.minimumHeight = 150
    self.targetTable.setStyleSheet("QTableView::item:selected{background-color: #ff7f7f; color: black};")
    self.layout().addWidget(self.targetTable)
  
  def cleanup(self):
    self.onDeactivation()
    self.currentTargets = None
    self.checkBoxList.clear()
    self.comboBoxList.clear()
  
  def setTargetTableSizeConstraints(self):
    self.targetTable.horizontalHeader().setResizeMode(qt.QHeaderView.Stretch)
    self.targetTable.horizontalHeader().setResizeMode(0, qt.QHeaderView.Fixed)
    self.targetTable.horizontalHeader().setResizeMode(1, qt.QHeaderView.ResizeToContents)
    self.targetTable.horizontalHeader().setResizeMode(2, qt.QHeaderView.Stretch)
    self.targetTable.horizontalHeader().setResizeMode(3, qt.QHeaderView.ResizeToContents)
    self.targetTable.horizontalHeader().setResizeMode(4, qt.QHeaderView.ResizeToContents)

  def setupConnections(self):
    self.targetTable.connect('clicked(QModelIndex)', self.onTargetSelectionChanged)

  @onModuleSelected(ProstateCryoAblationPlugin.MODULE_NAME)
  def onLayoutChanged(self, layout=None):
    self.disableTargetMovingMode()

  @vtk.calldata_type(vtk.VTK_STRING)
  def onCaseClosed(self, caller, event, callData):
    self.currentTargets = None

  def onActivation(self):
    super(TargetsDefinitionTable, self).onActivation()
    self.moveTargetMode = False
    self.currentlyMovedTargetModelIndex = None
    self.connectKeyEventObservers()
    if self.currentTargets:
      self.onTargetSelectionChanged()

  def onDeactivation(self):
    super(TargetsDefinitionTable, self).onDeactivation()
    self.disableTargetMovingMode()
    self.disconnectKeyEventObservers()

  def connectKeyEventObservers(self):
    interactors = [self.yellowSliceViewInteractor]
    if self.layoutManager.layout == constants.LAYOUT_FOUR_UP:
      interactors += [self.redSliceViewInteractor, self.greenSliceViewInteractor]
    for interactor in interactors:
      self.keyPressEventObservers[interactor] = interactor.AddObserver("KeyPressEvent", self.onKeyPressedEvent)
      self.keyReleaseEventObservers[interactor] = interactor.AddObserver("KeyReleaseEvent", self.onKeyReleasedEvent)

  def disconnectKeyEventObservers(self):
    for interactor, tag in self.keyPressEventObservers.iteritems():
      interactor.RemoveObserver(tag)
    for interactor, tag in self.keyReleaseEventObservers.iteritems():
      interactor.RemoveObserver(tag)

  def onKeyPressedEvent(self, caller, event):
    if not caller.GetKeySym() == 'd':
      return
    if not self.targetTableModel.computeCursorDistances:
      self.targetTableModel.computeCursorDistances = True
      self.calcCursorTargetsDistance()
      self.crosshairButton.addEventObserver(self.crosshairButton.CursorPositionModifiedEvent,
                                            self.calcCursorTargetsDistance)

  def onKeyReleasedEvent(self, caller, event):
    if not caller.GetKeySym() == 'd':
      return
    self.targetTableModel.computeCursorDistances = False
    self.crosshairButton.removeEventObserver(self.crosshairButton.CursorPositionModifiedEvent,
                                             self.calcCursorTargetsDistance)

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def calcCursorTargetsDistance(self, caller, event, callData):
    if not self.targetTableModel.computeCursorDistances:
      return
    ras = xyz = [0.0, 0.0, 0.0]
    insideView = callData.GetCursorPositionRAS(ras)
    sliceNode = callData.GetCursorPositionXYZ(xyz)

    if not insideView or sliceNode not in [self.redSliceNode, self.yellowSliceNode, self.greenSliceNode]:
      self.targetTableModel.cursorPosition = None
      return
    self.targetTableModel.cursorPosition = ras

  def onTargetSelectionChanged(self, modelIndex=None):
    # onCurrentResultSelected event
    if not modelIndex:
      self.getAndSelectTargetFromTable()
      return
    if self.moveTargetMode is True and modelIndex != self.currentlyMovedTargetModelIndex:
      self.disableTargetMovingMode()
    self.lastSelectedModelIndex = modelIndex
    if not self.currentTargets:
      self.currentTargets = self.session.data.intraOpTargets
    self.jumpSliceNodesToNthTarget(modelIndex.row())
    self.targetTableModel.currentTargetIndex = self.lastSelectedModelIndex.row()
    self.updateSelection(self.lastSelectedModelIndex.row())

  def updateSelection(self, row):
    self.targetTable.clearSelection()
    first = self.targetTable.model().index(row, 0)
    second = self.targetTable.model().index(row, 1)

    selection = qt.QItemSelection(first, second)
    self.targetTable.selectionModel().select(selection, qt.QItemSelectionModel.Select)

  def jumpSliceNodesToNthTarget(self, targetIndex):
    currentTargetsSliceNodes = []
    if self.layoutManager.layout in [constants.LAYOUT_RED_SLICE_ONLY, constants.LAYOUT_SIDE_BY_SIDE]:
      targets = self.session.data.intraOpTargets
      if self.session.currentSeries and self.session.seriesTypeManager.isVibe(self.session.currentSeries):
        targets = self.targetTableModel.targetList
      self.jumpSliceNodeToTarget(self.redSliceNode, targets, targetIndex)
      self.logic.setTargetSelected(targets, selected=False)
      targets.SetNthFiducialSelected(targetIndex, True)

    if self.layoutManager.layout == constants.LAYOUT_SIDE_BY_SIDE:
      currentTargetsSliceNodes = [self.yellowSliceNode]
    elif self.layoutManager.layout == constants.LAYOUT_FOUR_UP:
      currentTargetsSliceNodes = [self.redSliceNode, self.yellowSliceNode, self.greenSliceNode]

    for sliceNode in currentTargetsSliceNodes:
      self.jumpSliceNodeToTarget(sliceNode, self.currentTargets, targetIndex)
    self.logic.setTargetSelected(self.currentTargets, selected=False)
    self.currentTargets.SetNthFiducialSelected(targetIndex, True)

  def getAndSelectTargetFromTable(self):
    modelIndex = None
    if self.lastSelectedModelIndex:
      modelIndex = self.lastSelectedModelIndex
    else:
      if self.targetTableModel.rowCount():
        modelIndex = self.targetTableModel.index(0,0)
    if modelIndex:
      self.targetTable.clicked(modelIndex)

  def onMoveTargetRequest(self, modelIndex):
    if self.moveTargetMode:
      self.disableTargetMovingMode()
      if self.currentlyMovedTargetModelIndex != modelIndex:
        self.onMoveTargetRequest(modelIndex)
      self.currentlyMovedTargetModelIndex = None
    else:
      self.currentlyMovedTargetModelIndex = modelIndex
      self.enableTargetMovingMode()

  def enableTargetMovingMode(self):
    self.clearTargetMovementObserverAndAnnotations()
    targetName = self.targetTableModel.targetList.GetNthFiducialLabel(self.currentlyMovedTargetModelIndex.row())

    widgets = [self.yellowWidget] if self.layoutManager.layout == constants.LAYOUT_SIDE_BY_SIDE else \
                 [self.redWidget, self.yellowWidget, self.greenWidget]
    for widget in widgets:
      sliceView = widget.sliceView()
      interactor = sliceView.interactorStyle().GetInteractor()
      observer = interactor.AddObserver(vtk.vtkCommand.LeftButtonReleaseEvent, self.onViewerClickEvent)
      sliceView.setCursor(qt.Qt.CrossCursor)
      annotation = SliceAnnotation(widget, "Target Movement Mode (%s)" % targetName, opacity=0.5,
                                   verticalAlign="top", horizontalAlign="center")
      self.mouseReleaseEventObservers[widget] = (observer, annotation)
    self.moveTargetMode = True

  def disableTargetMovingMode(self):
    self.clearTargetMovementObserverAndAnnotations()
    self.mouseReleaseEventObservers = {}
    self.moveTargetMode = False

  def clearTargetMovementObserverAndAnnotations(self):
    for widget, (observer, annotation) in self.mouseReleaseEventObservers.iteritems():
      sliceView = widget.sliceView()
      interactor = sliceView.interactorStyle().GetInteractor()
      interactor.RemoveObserver(observer)
      sliceView.setCursor(qt.Qt.ArrowCursor)
      annotation.remove()

  def onViewerClickEvent(self, observee=None, event=None):
    posXY = observee.GetEventPosition()
    widget = self.getWidgetForInteractor(observee)
    if self.currentlyMovedTargetModelIndex is not None:
      posRAS = self.xyToRAS(widget.sliceLogic(), posXY)
      self.targetTableModel.targetList.SetNthFiducialPositionFromArray(self.currentlyMovedTargetModelIndex.row(),
                                                                       posRAS)
      guidance = self.targetTableModel.getOrCreateNewGuidanceComputation(
        self.targetTableModel.targetList)
      needleSnapPosition = guidance.getNeedleEndPos(self.currentlyMovedTargetModelIndex.row())
      self.targetTableModel.targetList.SetNthFiducialPositionFromArray(self.currentlyMovedTargetModelIndex.row(),
                                                                       needleSnapPosition)
      self.invokeEvent(self.TargetPosUpdatedEvent)

    self.disableTargetMovingMode()

  def getWidgetForInteractor(self, observee):
    for widget in self.mouseReleaseEventObservers.keys():
      sliceView = widget.sliceView()
      interactor = sliceView.interactorStyle().GetInteractor()
      if interactor is observee:
        return widget
    return None

