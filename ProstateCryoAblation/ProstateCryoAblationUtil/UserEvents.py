import vtk, slicer

class ProstateCryoAblationUserEvents(object):
  InitiateTargetingEvent = vtk.vtkCommand.UserEvent + 100
