import qt
import vtk
import slicer
from ...constants import ProstateCryoAblationConstants as constants
from ..base import ProstateCryoAblationPlugin

from SlicerDevelopmentToolboxUtils.helpers import SliceAnnotation
from SlicerDevelopmentToolboxUtils.widgets import TargetCreationWidget
from targets import ProstateCryoAblationTargetTablePlugin


class ProstateCryoAblationTargetingPlugin(ProstateCryoAblationPlugin):

  NAME = "Targeting"
  TargetingStartedEvent = vtk.vtkCommand.UserEvent + 335
  TargetingFinishedEvent = vtk.vtkCommand.UserEvent + 336

  def __init__(self, prostateCryoAblationSession):
    super(ProstateCryoAblationTargetingPlugin, self).__init__(prostateCryoAblationSession)
    
  def setup(self):
    self.targetTablePlugin = ProstateCryoAblationTargetTablePlugin(self.session, movingEnabled=True)
    self.addPlugin(self.targetTablePlugin)

    self.targetingGroupBox = qt.QGroupBox("Target Placement")
    self.targetingGroupBoxLayout = qt.QFormLayout()
    self.targetingGroupBox.setLayout(self.targetingGroupBoxLayout)
    self.fiducialsWidget = TargetCreationWidget(DEFAULT_FIDUCIAL_LIST_NAME="IntraOpTargets",
                                                ICON_SIZE=qt.QSize(36, 36))
    self.fiducialsWidget.addEventObserver(self.fiducialsWidget.StartedEvent, self.onTargetingStarted)
    self.fiducialsWidget.addEventObserver(self.fiducialsWidget.FinishedEvent, self.onTargetingFinished)
    self.fiducialsWidget.targetListSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onFiducialListSelected)
    self.targetingGroupBoxLayout.addRow(self.targetTablePlugin)
    self.targetingGroupBoxLayout.addRow(self.fiducialsWidget)
    self.layout().addWidget(self.targetingGroupBox, 1, 0, 2, 2)

  def onActivation(self):
    super(ProstateCryoAblationTargetingPlugin, self).onActivation()
    self.fiducialsWidget.table.visible = False
    self.fiducialsWidget.currentNode = self.session.movingTargets
    self.targetTablePlugin.visible = True
    self.targetTablePlugin.currentTargets = self.session.movingTargets
    self.targetingGroupBox.visible = True

  def onDeactivation(self):
    super(ProstateCryoAblationTargetingPlugin, self).onDeactivation()
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
      self.fiducialsWidget.invokeEvent(slicer.vtkMRMLMarkupsNode().MarkupAddedEvent)
    pass

  def onEndTargetRemove(self, caller, event):
    #self.displayForTargets[fiducialIndex] = qt.Qt.Unchecked
    self.fiducialsWidget.invokeEvent(slicer.vtkMRMLMarkupsNode().MarkupRemovedEvent)

  def onTargetingStarted(self, caller, event):
    self.addSliceAnnotations()
    self.targetTablePlugin.visible = False
    self.targetTablePlugin.disableTargetMovingMode()
    self.fiducialsWidget.table.visible = True
    self.invokeEvent(self.TargetingStartedEvent)

  def onTargetingFinished(self, caller, event):
    self.removeSliceAnnotations()
    if self.fiducialsWidget.hasTargetListAtLeastOneTarget():
      self.session.movingTargets = self.fiducialsWidget.currentNode
      self.session.setupLoadedTargets()
      self.fiducialsWidget.table.visible = False
      self.targetTablePlugin.visible = True
      self.targetTablePlugin.currentTargets = self.fiducialsWidget.currentNode
    else:
      self.session.movingTargets = None
    self.invokeEvent(self.TargetingFinishedEvent)