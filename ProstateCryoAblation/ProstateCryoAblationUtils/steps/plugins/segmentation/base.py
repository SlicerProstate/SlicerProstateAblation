import vtk
from ...base import ProstateCryoAblationPlugin


class ProstateCryoAblationSegmentationPluginBase(ProstateCryoAblationPlugin):

  SegmentationStartedEvent = vtk.vtkCommand.UserEvent + 435
  SegmentationFinishedEvent = vtk.vtkCommand.UserEvent + 436

  def __init__(self):
    super(ProstateCryoAblationSegmentationPluginBase, self).__init__()

  def startSegmentation(self):
    raise NotImplementedError

  def onSegmentationStarted(self, caller, event):
    self.invokeEvent(self.SegmentationStartedEvent)

  @vtk.calldata_type(vtk.VTK_OBJECT)
  def onSegmentationFinished(self, caller, event, labelNode):
    self.invokeEvent(self.SegmentationFinishedEvent, labelNode)
