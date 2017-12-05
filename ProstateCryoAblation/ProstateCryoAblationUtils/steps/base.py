import vtk, qt, logging
from SlicerDevelopmentToolboxUtils.decorators import beforeRunProcessEvents, onModuleSelected
from SlicerDevelopmentToolboxUtils.module.base import WidgetBase
from SlicerDevelopmentToolboxUtils.module.logic import SessionBasedLogicBase

from ProstateCryoAblationUtils.constants import ProstateCryoAblationConstants as constants
#from ProstateCryoAblationUtils.session import ProstateCryoAblationSession
from SlicerDevelopmentToolboxUtils.icons import Icons
from SlicerDevelopmentToolboxUtils.mixins import ModuleWidgetMixin, ModuleLogicMixin, GeneralModuleMixin

class ProstateCryoAblationWidgetBase(qt.QWidget, ModuleWidgetMixin):

  MODULE_NAME = constants.MODULE_NAME
  LogicClass = None
  LayoutClass = qt.QGridLayout
  AvailableLayoutsChangedEvent = vtk.vtkCommand.UserEvent + 4233
  ActivatedEvent = vtk.vtkCommand.UserEvent + 150
  
  @property
  def active(self):
    self._activated = getattr(self, "_activated", False)
    return self._activated

  @active.setter
  def active(self, value):
    if self.active == value:
      return
    self._activated = value
    logging.debug("%s %s" % ("activated" if self.active else "deactivate", self.NAME))
    self.invokeEvent(self.ActivatedEvent if self.active else self.DeactivatedEvent)
    if self.active:
      self.onActivation()
    else:
      self.onDeactivation()
  
  def __init__(self, session):
    super(ProstateCryoAblationWidgetBase, self).__init__()
    if self.LogicClass:
      self.logic = self.LogicClass(session)
    self.setLayout(self.LayoutClass())  
    self.session = session
    self._plugins = []
    
  def setup(self):
    self.setupSliceWidgets()
    self.addSessionObservers()
    self.setupConnections()
    self.setupIcons()
    self.setupAdditionalViewSettingButtons()
  
  def setupIcons(self):
    pass
  
  def setupSliceWidgets(self):
    self.createSliceWidgetClassMembers("Red")
    self.createSliceWidgetClassMembers("Yellow")
    self.createSliceWidgetClassMembers("Green")

  def setupAdditionalViewSettingButtons(self):
    pass

  def addSessionObservers(self):
    self.session.addEventObserver(self.session.NewCaseStartedEvent, self.onNewCaseStarted)
    self.session.addEventObserver(self.session.CaseOpenedEvent, self.onCaseOpened)
    self.session.addEventObserver(self.session.CloseCaseEvent, self.onCaseClosed)
    self.session.addEventObserver(self.session.NewImageSeriesReceivedEvent, self.onNewImageSeriesReceived)
    self.session.addEventObserver(self.session.CurrentSeriesChangedEvent, self.onCurrentSeriesChanged)

  def removeSessionEventObservers(self):
    self.session.removeEventObserver(self.session.NewCaseStartedEvent, self.onNewCaseStarted)
    self.session.removeEventObserver(self.session.CaseOpenedEvent, self.onCaseOpened)
    self.session.removeEventObserver(self.session.CloseCaseEvent, self.onCaseClosed)
    self.session.removeEventObserver(self.session.NewImageSeriesReceivedEvent, self.onNewImageSeriesReceived)
    self.session.removeEventObserver(self.session.CurrentSeriesChangedEvent, self.onCurrentSeriesChanged)
  
  def getSetting(self, setting, moduleName=None, default=None):
    return GeneralModuleMixin.getSetting(self, setting, moduleName=moduleName if moduleName else self.MODULE_NAME,
                                         default=default)

  def setSetting(self, setting, value, moduleName=None):
    return GeneralModuleMixin.setSetting(self, setting, value,
                                         moduleName=moduleName if moduleName else self.MODULE_NAME)
  
  def onNewCaseStarted(self, caller, event):
    pass

  def onCaseOpened(self, caller, event):
    pass

  @vtk.calldata_type(vtk.VTK_STRING)
  def onCaseClosed(self, caller, event, callData):
    pass
  
  def setupConnections(self):
    pass
  
  def onActivation(self):
    self.layoutManager.layoutChanged.connect(self.onLayoutChanged)
    self.activePlugin()

  def onDeactivation(self):
    self.layoutManager.layoutChanged.disconnect(self.onLayoutChanged)
    self.deactivePlugin()

  def activePlugin(self):
    for plugin in self._plugins:
      plugin.active = True
      
  def deactivePlugin(self):
    for plugin in self._plugins:
      plugin.active = False
  
  def addPlugin(self, plugin):
    self._plugins.append(plugin)    
          
  @onModuleSelected(constants.MODULE_NAME)
  def onLayoutChanged(self, layout=None):
    pass

  def setAvailableLayouts(self, layouts):
    if not all([l in constants.ALLOWED_LAYOUTS for l in layouts]):
      raise ValueError("Not all of the delivered layouts are allowed to be used in ProstateCryoAblation")
    self.invokeEvent(self.AvailableLayoutsChangedEvent, str(layouts))

  def addPlugin(self, plugin):
    plugin.addEventObserver(self.AvailableLayoutsChangedEvent, self.onPluginAvailableLayoutChanged)

  @vtk.calldata_type(vtk.VTK_STRING)
  def onPluginAvailableLayoutChanged(self, caller, event, callData):
    self.invokeEvent(self.AvailableLayoutsChangedEvent, callData)

  def resetViewSettingButtons(self):
    pass

  @vtk.calldata_type(vtk.VTK_STRING)
  def onNewImageSeriesReceived(self, caller, event, callData):
    pass

  @vtk.calldata_type(vtk.VTK_STRING)
  def onCurrentSeriesChanged(self, caller, event, callData=None):
    pass

  def setupFourUpView(self, volume, clearLabels=True):
    self.setBackgroundToVolumeID(volume.GetID(), clearLabels)
    self.layoutManager.setLayout(constants.LAYOUT_FOUR_UP)

  def setBackgroundToVolumeID(self, volumeID, clearLabels=True):
    for compositeNode, sliceNode in zip(self._compositeNodes, self._sliceNodes):
      if clearLabels:
        compositeNode.SetLabelVolumeID(None)
      sliceNode.SetUseLabelOutline(True)
      compositeNode.SetForegroundVolumeID(None)
      compositeNode.SetBackgroundVolumeID(volumeID)
    self.setDefaultOrientation()

  def setDefaultOrientation(self):
    self.redSliceNode.SetOrientationToAxial()
    self.yellowSliceNode.SetOrientationToSagittal()
    self.greenSliceNode.SetOrientationToCoronal()
    self.updateFOV() # TODO: shall not be called here

  def setAxialOrientation(self):
    for sliceNode in self._sliceNodes:
      sliceNode.SetOrientationToAxial()
    self.updateFOV() # TODO: shall not be called here

  def updateFOV(self):
    if self.layoutManager.layout == constants.LAYOUT_RED_SLICE_ONLY:
      self.setDefaultFOV(self.redSliceLogic)
    elif self.layoutManager.layout == constants.LAYOUT_SIDE_BY_SIDE:
      self.setDefaultFOV(self.redSliceLogic)
      self.setDefaultFOV(self.yellowSliceLogic)
    elif self.layoutManager.layout == constants.LAYOUT_FOUR_UP:
      self.setDefaultFOV(self.redSliceLogic)
      self.yellowSliceLogic.FitSliceToAll()
      self.greenSliceLogic.FitSliceToAll()

  @beforeRunProcessEvents
  def setDefaultFOV(self, sliceLogic, factor=0.5):
    sliceLogic.FitSliceToAll()
    FOV = sliceLogic.GetSliceNode().GetFieldOfView()
    self.setFOV(sliceLogic, [FOV[0] * factor, FOV[1] * factor, FOV[2]])

  def setupRedSlicePreview(self, selectedSeries):
    self.layoutManager.setLayout(constants.LAYOUT_RED_SLICE_ONLY)
    self.hideAllFiducialNodes()
    try:
      result = self.session.data.getResultsBySeries(selectedSeries)[0]
      volume = result.volumes.fixed
    except IndexError:
      volume = self.session.getOrCreateVolumeForSeries(selectedSeries)
    self.setBackgroundToVolumeID(volume.GetID())


class ProstateCryoAblationStep(ProstateCryoAblationWidgetBase):

  def __init__(self, prostateCryoAblationSession):
    self.viewSettingButtons = []
    iconSize = qt.QSize(36, 36)
    self.finishStepIcon = Icons.start
    self.backIcon = Icons.back
    self.backButton = self.createButton("", icon=self.backIcon, iconSize=iconSize,
                                        toolTip="Return to last step")
    self.finishStepButton = self.createButton("", icon=self.finishStepIcon, iconSize=iconSize,
                                              toolTip="Confirm the targeting")
    self.parameterNode.SetAttribute("Name", self.NAME)
    super(ProstateCryoAblationStep, self).__init__(prostateCryoAblationSession)

  def addNavigationButtons(self):
    self.finishStepButton.setFixedHeight(45)
    self.layout().addWidget(self.createHLayout([self.backButton, self.finishStepButton]))

  def resetAndInitialize(self):
    pass

class ProstateCryoAblationLogicBase(ModuleLogicMixin):

  MODULE_NAME = constants.MODULE_NAME
  
  def __init__(self, session):
    super(ProstateCryoAblationLogicBase, self).__init__()
    self.session = session

class ProstateCryoAblationPlugin(ProstateCryoAblationWidgetBase):

  def __init__(self, session):
    super(ProstateCryoAblationPlugin, self).__init__(session)
    