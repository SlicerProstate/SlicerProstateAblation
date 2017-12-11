import qt
import vtk
import slicer
import numpy
from ...constants import ProstateCryoAblationConstants as constants
from ..base import ProstateCryoAblationPlugin

from SlicerDevelopmentToolboxUtils.helpers import SliceAnnotation
from SlicerDevelopmentToolboxUtils.widgets import TargetCreationWidget
from SlicerDevelopmentToolboxUtils.icons import Icons
from targetsDefinitionTable import TargetsDefinitionTable


class TargetsDefinitionPlugin(ProstateCryoAblationPlugin):

  NAME = "Targeting"
  TargetingStartedEvent = vtk.vtkCommand.UserEvent + 335
  TargetingFinishedEvent = vtk.vtkCommand.UserEvent + 336

  def __init__(self, prostateCryoAblationSession):
    super(TargetsDefinitionPlugin, self).__init__(prostateCryoAblationSession)
    
  def setup(self):
    self.targetTablePlugin = TargetsDefinitionTable(self.session, movingEnabled=True)
    self.addPlugin(self.targetTablePlugin)

    self.targetingGroupBox = qt.QGroupBox("Target Placement")
    self.targetingGroupBoxLayout = qt.QFormLayout()
    self.targetingGroupBox.setLayout(self.targetingGroupBoxLayout)
    self.fiducialsWidget = TargetCreationWidget(DEFAULT_FIDUCIAL_LIST_NAME="IntraOpTargets",
                                                ICON_SIZE=qt.QSize(36, 36))
    self.fiducialsWidget.addEventObserver(self.fiducialsWidget.StartedEvent, self.onTargetingStarted)
    self.fiducialsWidget.addEventObserver(self.fiducialsWidget.FinishedEvent, self.onTargetingFinished)
    self.fiducialsWidget.targetListSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onFiducialListSelected)
    self.targetDistanceWidget = qt.QListWidget()
    self.targetDistanceWidget.setWindowTitle("Distances Between Targets")
    #self.showTargetDistanceIcon = self.createIcon('icon-distance.png')
    #self.showTargetDistanceButton = self.createButton("", enabled=True, icon=self.showTargetDistanceIcon, iconSize=qt.QSize(24, 24),
    #                                              toolTip="Start placing targets")
    self.targetingGroupBoxLayout.addRow(self.targetTablePlugin)
    self.targetingGroupBoxLayout.addRow(self.fiducialsWidget)
    self.layout().addWidget(self.targetingGroupBox, 1, 0, 2, 2)
    self.layout().addWidget(self.targetDistanceWidget)

  def onActivation(self):
    super(TargetsDefinitionPlugin, self).onActivation()
    self.fiducialsWidget.table.visible = False
    self.fiducialsWidget.currentNode = self.session.movingTargets
    self.targetTablePlugin.visible = True
    self.targetTablePlugin.currentTargets = self.session.movingTargets
    self.calculateTargetsDistance()
    self.targetingGroupBox.visible = True
    self.targetDistanceWidget.visible = True

  def cleanup(self):
    self.fiducialsWidget.reset()
    self.targetTablePlugin.cleanup()

  def onDeactivation(self):
    super(TargetsDefinitionPlugin, self).onDeactivation()
    self.fiducialsWidget.reset()
    self.removeSliceAnnotations()

  def addSliceAnnotations(self):
    self.removeSliceAnnotations()
    widgets = [self.yellowWidget] if self.layoutManager.layout == constants.LAYOUT_SIDE_BY_SIDE else \
      [self.redWidget, self.yellowWidget, self.greenWidget]
    for widget in widgets:
      self.sliceAnnotations.append(SliceAnnotation(widget, "Targeting Mode", opacity=0.5, verticalAlign="top",
                                                   horizontalAlign="center"))

  def removeSliceAnnotations(self):
    self.sliceAnnotations = getattr(self, "sliceAnnotations", [])
    for annotation in self.sliceAnnotations:
      annotation.remove()
    self.sliceAnnotations = []

  def calculateTargetsDistance(self):
    self.targetDistanceWidget.clear()
    if self.targetTablePlugin.currentTargets is not None:
      numberOfTargets = self.targetTablePlugin.currentTargets.GetNumberOfFiducials()
      for targetIndex_A in range(numberOfTargets):
        for targetIndex_B in range(targetIndex_A+1, numberOfTargets):
          tAName = self.targetTablePlugin.currentTargets.GetNthFiducialLabel(targetIndex_A)
          tBName = self.targetTablePlugin.currentTargets.GetNthFiducialLabel(targetIndex_B)
          posA = 3*[0.0]
          posB = 3*[0.0]
          self.targetTablePlugin.currentTargets.GetNthFiducialPosition(targetIndex_A, posA)
          self.targetTablePlugin.currentTargets.GetNthFiducialPosition(targetIndex_B, posB)
          dist = numpy.linalg.norm(numpy.array(posA)-numpy.array(posB))/10.0
          itemString = str(tAName) + " -> " +  str(tBName) + ": " + str(dist) + "cm"
          tmpWidgetItem = qt.QListWidgetItem(itemString)
          self.targetDistanceWidget.addItem(tmpWidgetItem)
    pass

  def onFiducialListSelected(self, node):
    if node:
      self.fiducialsWidget.currentNode = node
      self.fiducialsWidget.currentNode.AddObserver(slicer.vtkMRMLMarkupsNode().MarkupAddedEvent,
                                                   self.onEndTargetPlacement)
      self.fiducialsWidget.currentNode.AddObserver(slicer.vtkMRMLMarkupsNode().MarkupRemovedEvent,
                                                   self.onEndTargetRemove)

  def onEndTargetPlacement(self,interactionNode = None, event = None):
    if self.fiducialsWidget.currentNode:
      currentTargetIndex = self.fiducialsWidget.currentNode.GetNumberOfFiducials()-1
      guidance= self.targetTablePlugin.targetTableModel.getOrCreateNewGuidanceComputation(self.fiducialsWidget.currentNode)
      needleSnapPosition = guidance.getNeedleEndPos(currentTargetIndex)
      self.fiducialsWidget.currentNode.SetNthFiducialPositionFromArray(currentTargetIndex,needleSnapPosition)
      self.session.displayForTargets[self.fiducialsWidget.currentNode.GetNthMarkupID(currentTargetIndex)] = qt.Qt.Unchecked
      self.session.needleTypeForTargets[self.fiducialsWidget.currentNode.GetNthMarkupID(currentTargetIndex)] = self.session.ISSEEDTYPE
      self.fiducialsWidget.invokeEvent(slicer.vtkMRMLMarkupsNode().MarkupAddedEvent)
    pass

  @vtk.calldata_type(vtk.VTK_INT)
  def onEndTargetRemove(self, caller, event, callData):
    tempCheckBoxList = self.targetTablePlugin.checkBoxList.copy()
    tempComboBoxList = self.targetTablePlugin.comboBoxList.copy()
    tempDisplayForTargets = self.session.displayForTargets.copy()
    tempNeedleTypeForTargets = self.session.needleTypeForTargets.copy()

    self.targetTablePlugin.checkBoxList.clear()
    self.targetTablePlugin.comboBoxList.clear()
    self.session.displayForTargets.clear()
    self.session.needleTypeForTargets.clear()
    for index in range(self.fiducialsWidget.currentNode.GetNumberOfFiducials()):
      key = self.fiducialsWidget.currentNode.GetNthMarkupID(index)
      if key is not None:
        self.targetTablePlugin.checkBoxList[key] = tempCheckBoxList.get(key)
        self.targetTablePlugin.comboBoxList[key] = tempComboBoxList.get(key)
        self.session.displayForTargets[key] = tempDisplayForTargets.get(key)
        self.session.needleTypeForTargets[key] = tempNeedleTypeForTargets.get(key)
    self.fiducialsWidget.invokeEvent(slicer.vtkMRMLMarkupsNode().MarkupRemovedEvent)

  def onTargetingStarted(self, caller, event):
    self.invokeEvent(self.TargetingStartedEvent)
    self.addSliceAnnotations()
    self.targetTablePlugin.visible = False
    self.targetTablePlugin.disableTargetMovingMode()
    self.targetDistanceWidget.visible = True
    self.fiducialsWidget.table.visible = True

  def onTargetingFinished(self, caller, event):
    self.removeSliceAnnotations()
    if self.fiducialsWidget.hasTargetListAtLeastOneTarget():
      self.session.movingTargets = self.fiducialsWidget.currentNode
      self.session.setupLoadedTargets()
      self.fiducialsWidget.table.visible = False
      self.targetTablePlugin.visible = True
      self.targetTablePlugin.currentTargets = self.fiducialsWidget.currentNode
      self.calculateTargetsDistance()
    else:
      self.session.movingTargets = None
    self.invokeEvent(self.TargetingFinishedEvent)