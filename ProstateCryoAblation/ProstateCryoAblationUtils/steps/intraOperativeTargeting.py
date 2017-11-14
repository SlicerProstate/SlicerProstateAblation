import os
import ast
import qt
import slicer
import vtk
from ..UserEvents import ProstateCryoAblationUserEvents
from ..constants import ProstateCryoAblationConstants
from ProstateCryoAblationUtils.steps.base import ProstateCryoAblationLogicBase,ProstateCryoAblationStep
from SlicerDevelopmentToolboxUtils.helpers import SliceAnnotation
from SlicerDevelopmentToolboxUtils.decorators import onModuleSelected
from SlicerDevelopmentToolboxUtils.mixins import ModuleLogicMixin
from ProstateCryoAblationUtils.steps.plugins.targeting import ProstateCryoAblationTargetingPlugin
import numpy

class ProstateCryoAblationTargetingStepLogic(ProstateCryoAblationLogicBase):
  
  def __init__(self):
    super(ProstateCryoAblationTargetingStepLogic, self).__init__()
        
class ProstateCryoAblationTargetingStep(ProstateCryoAblationStep):

  NAME = "Targeting"
  NEEDLE_NAME = 'NeedlePath'
  AFFECTEDAREA_NAME = "AffectedArea"
  LogicClass = ProstateCryoAblationTargetingStepLogic
  LayoutClass = qt.QVBoxLayout
  HIDENEEDLE = 0
  ICESEED = 1
  ICEROD = 2

  @property
  def NeedleType(self):
    return self._NeedleType

  @NeedleType.setter
  def NeedleType(self, type):
    self._NeedleType = type

  def __init__(self):
    self.modulePath = os.path.dirname(slicer.util.modulePath(self.MODULE_NAME)).replace(".py", "")
    self.affectiveZoneIcon = self.createIcon('icon-needle.png')
    self.segmentationEditor = slicer.qMRMLSegmentEditorWidget()
    self.segmentationEditorNoneButton = None
    self.segmentationEditorShow3DButton = None
    self.segmentEditorNode = None
    super(ProstateCryoAblationTargetingStep, self).__init__()
    self.needleModelNode = None
    self.affectedAreaModelNode = None
    self.segmentModelNode = None
    self._NeedleType = self.ICESEED
    self.clearOldNodesByName(self.NEEDLE_NAME)
    self.resetAndInitialize()
  
  def clearOldNodesByName(self, name):
    collection = slicer.mrmlScene.GetNodesByName(name)
    for index in range(collection.GetNumberOfItems()):
      slicer.mrmlScene.RemoveNode(collection.GetItemAsObject(index))
  
  def checkAndCreateNeedleAndSegModelNode(self):
    if self.needleModelNode is None:
      self.needleModelNode = ModuleLogicMixin.createModelNode(self.NEEDLE_NAME)
    if (self.needleModelNode.GetScene() is None) or (not self.needleModelNode.GetScene() == slicer.mrmlScene):
      slicer.mrmlScene.AddNode(self.needleModelNode)
    if self.needleModelNode.GetDisplayNode() is None:
      ModuleLogicMixin.createAndObserveDisplayNode(self.needleModelNode, displayNodeClass=slicer.vtkMRMLModelDisplayNode)
      self.needleModelNode.GetDisplayNode().SetColor(1.0, 0.0, 0.0)
      
    if self.affectedAreaModelNode is None:
      self.affectedAreaModelNode = ModuleLogicMixin.createModelNode(self.AFFECTEDAREA_NAME)
    if (self.affectedAreaModelNode.GetScene() is None) or (not self.affectedAreaModelNode.GetScene() == slicer.mrmlScene):
      slicer.mrmlScene.AddNode(self.affectedAreaModelNode)
    if self.affectedAreaModelNode.GetDisplayNode() is None:
      ModuleLogicMixin.createAndObserveDisplayNode(self.affectedAreaModelNode, displayNodeClass=slicer.vtkMRMLModelDisplayNode)
      self.affectedAreaModelNode.GetDisplayNode().SetOpacity(0.5)
      self.affectedAreaModelNode.GetDisplayNode().SetColor(0.0,1.0,0.0)
      
    if self.segmentModelNode is None:
      # Create segmentation
      self.segmentModelNode = slicer.vtkMRMLSegmentationNode()
      slicer.mrmlScene.AddNode(self.segmentModelNode)
      self.segmentModelNode.CreateDefaultDisplayNodes()  # only needed for display
      self.segmentModelNode.CreateDefaultStorageNode()
      self.segmentModelNode.SetName("IntraOpSegmentation")
    if (self.segmentModelNode.GetScene() is None) or (not self.segmentModelNode.GetScene() == slicer.mrmlScene):
      slicer.mrmlScene.AddNode(self.segmentModelNode) 
    if self.segmentModelNode.GetDisplayNode() is None:
      ModuleLogicMixin.createAndObserveDisplayNode(self.segmentModelNode,
                                                   displayNodeClass=slicer.vtkMRMLSegmentationDisplayNode)
    if self.segmentEditorNode is None:
      self.segmentEditorNode = slicer.vtkMRMLSegmentEditorNode()
      slicer.mrmlScene.AddNode(self.segmentEditorNode)
    if (self.segmentEditorNode.GetScene() is None) or (not self.segmentEditorNode.GetScene() == slicer.mrmlScene):
      slicer.mrmlScene.AddNode(self.segmentEditorNode)   
    self.segmentationEditor.setMRMLScene(slicer.mrmlScene)
    self.segmentationEditor.setMRMLSegmentEditorNode(self.segmentEditorNode)
    
  def resetAndInitialize(self):
    self.session.retryMode = False
    self.checkAndCreateNeedleAndSegModelNode()

  def setup(self):
    super(ProstateCryoAblationTargetingStep, self).setup()
    self.setupTargetingPlugin()
    self.setupSegmentationWidget()
    self.setupAdditionalViewSettingButtons()
    self.addNavigationButtons()
    self.layout().addStretch(1)

  def setupTargetingPlugin(self):
    self.targetingPlugin = ProstateCryoAblationTargetingPlugin()
    self.targetingPlugin.addEventObserver(self.targetingPlugin.TargetingStartedEvent, self.onTargetingStarted)
    self.targetingPlugin.addEventObserver(self.targetingPlugin.TargetingFinishedEvent, self.onTargetingFinished)
    self.addPlugin(self.targetingPlugin)
    self.layout().addWidget(self.targetingPlugin)

  def setupSegmentationWidget(self):
    self.layout().addWidget(self.segmentationEditor)
    for child in self.segmentationEditor.children():
      if child.className() == 'QGroupBox':
        if child.title == 'Effects':
          self.segmentationEditorNoneButton = child.children()[1]
      if child.className() == 'ctkMenuButton':
        if child.text == ' Show 3D':
          self.segmentationEditorShow3DButton = child


  def setupAdditionalViewSettingButtons(self):
    iconSize = qt.QSize(24, 24)
    self.showAffectiveZoneButton = self.createButton("", icon=self.affectiveZoneIcon, iconSize=iconSize, checkable=True, toolTip="Display the effective ablation zone")
    self.viewSettingButtons = [self.showAffectiveZoneButton]
    pass
  
  def onBackButtonClicked(self):
    if self.session.retryMode:
      self.session.retryMode = False
    if self.session.previousStep:
      self.session.previousStep.active = True

  def onFinishStepButtonClicked(self):
    #To do, deactivate the drawing buttons when finish button clicked
    self.session.data.segmentModelNode = self.segmentationEditor.segmentationNode()
    self.segmentationEditorNoneButton.click()
    self.session.previousStep.active = True
  
  def setupConnections(self):
    super(ProstateCryoAblationTargetingStep, self).setupConnections()
    self.backButton.clicked.connect(self.onBackButtonClicked)
    self.finishStepButton.clicked.connect(self.onFinishStepButtonClicked)
    self.showAffectiveZoneButton.connect('toggled(bool)', self.onShowAffectiveZoneToggled)

  def GetIceBallRadius(self):
    needleRadius =[0.0]*3
    if self.NeedleType == self.HIDENEEDLE:
      needleRadius[0] = 0.0
      needleRadius[1] = 0.0
      needleRadius[2] = 0.0
    elif self.NeedleType == self.ICESEED:
      needleRadius[0] = 20.0 / 2.0
      needleRadius[1] = 20.0 / 2.0
      needleRadius[2] = 25.0 / 2.0
    elif self.NeedleType == self.ICEROD:
      needleRadius[0] = 25.0 / 2.0
      needleRadius[1] = 25.0 / 2.0
      needleRadius[2] = 35.0 / 2.0
    else:
      needleRadius[0] = 20.0 / 2.0
      needleRadius[1] = 20.0 / 2.0
      needleRadius[2] = 25.0 / 2.0
    return needleRadius

  def onShowAffectiveZoneToggled(self, checked):
    self.showNeedlePath = checked
    currentGuidanceComputation = self.targetingPlugin.targetTablePlugin.targetTableModel.currentGuidanceComputation
    if currentGuidanceComputation and self.needleModelNode and self.affectedAreaModelNode and self.session.approvedCoverTemplate and currentGuidanceComputation.targetList.GetNumberOfFiducials():
      ModuleLogicMixin.setNodeVisibility(self.needleModelNode, checked)
      ModuleLogicMixin.setNodeSliceIntersectionVisibility(self.needleModelNode, checked) 
      ModuleLogicMixin.setNodeVisibility(self.affectedAreaModelNode, checked)
      ModuleLogicMixin.setNodeSliceIntersectionVisibility(self.affectedAreaModelNode, checked)  
      needleModelAppend = vtk.vtkAppendPolyData()
      affectedBallAreaAppend = vtk.vtkAppendPolyData()
      zFrameTransformMatrix = self.session.data.zFrameRegistrationResult.transform.GetMatrixTransformToParent()
      # The offset and ellipsoid parameters are taken from the following source code
      # http://viewvc.slicer.org/viewvc.cgi/NAMICSandBox/trunk/IGTLoadableModules/ProstateNav/TransPerinealProstateCryoTemplate/vtkMRMLTransPerinealProstateCryoTemplateNode.cxx?revision=8043&view=markup
      affectedBallAreaRadius = self.GetIceBallRadius() # unit mm
      offsetFromTip = 5.0 #unit mm
      coneHeight = 5.0
      for targetIndex in range(currentGuidanceComputation.targetList.GetNumberOfFiducials()):
        targetPosition = [0.0,0.0,0.0]
        currentGuidanceComputation.targetList.GetNthFiducialPosition(targetIndex, targetPosition)
        (start, end, indexX, indexY, depth, inRange) = currentGuidanceComputation.computeNearestPath(targetPosition)
        needleDirection = (numpy.array(end) - numpy.array(start))/numpy.linalg.norm(numpy.array(end)-numpy.array(start))
        cone = vtk.vtkConeSource()
        cone.SetRadius(1.5)
        cone.SetResolution(6)
        cone.SetHeight(coneHeight)
        cone.CappingOff()
        cone.Update()
        transform = vtk.vtkTransform()
        transform.RotateY(-90)
        transform.RotateX(30)
        transform.Translate(-coneHeight / 2, 0.0, 0.0)
        tFilter0 = vtk.vtkTransformPolyDataFilter()
        tFilter0.SetInputData(cone.GetOutput())
        tFilter0.SetTransform(transform)
        tFilter0.Update()
        translatePart = start+depth*needleDirection
        for index, posElement in enumerate(translatePart):
          zFrameTransformMatrix.SetElement(index, 3, posElement)
        transform.SetMatrix(zFrameTransformMatrix)
        tFilter1 = vtk.vtkTransformPolyDataFilter()
        tFilter1.SetTransform(transform)
        tFilter1.SetInputData(tFilter0.GetOutput())
        tFilter1.Update()
        needleModelAppend.AddInputData(tFilter1.GetOutput())
        needleModelAppend.Update()
        pathTubeFilter = ModuleLogicMixin.createVTKTubeFilter(start, start+(depth-coneHeight)*needleDirection, radius=1.5, numSides=6)
        needleModelAppend.AddInputData(pathTubeFilter.GetOutput())
        needleModelAppend.Update()
        #End of needle model
        #--------------
        #--------------
        #Begin of affectedBallArea
        affectedBallArea = vtk.vtkParametricEllipsoid()
        affectedBallArea.SetXRadius(affectedBallAreaRadius[0])
        affectedBallArea.SetYRadius(affectedBallAreaRadius[1])
        affectedBallArea.SetZRadius(affectedBallAreaRadius[2])
        affectedBallAreaSource = vtk.vtkParametricFunctionSource()
        affectedBallAreaSource.SetParametricFunction(affectedBallArea)
        affectedBallAreaSource.SetScalarModeToV()
        affectedBallAreaSource.Update()
        translatePart = start+(depth+offsetFromTip-affectedBallAreaRadius[2])*needleDirection
        for index, posElement in enumerate(translatePart):
          zFrameTransformMatrix.SetElement(index, 3, posElement)
        transform.SetMatrix(zFrameTransformMatrix)
        tFilter2 = vtk.vtkTransformPolyDataFilter()
        tFilter2.SetTransform(transform)
        tFilter2.SetInputData(affectedBallAreaSource.GetOutput())
        tFilter2.Update()
        affectedBallAreaAppend.AddInputData(tFilter2.GetOutput())
        affectedBallAreaAppend.Update()

      self.needleModelNode.SetAndObservePolyData(needleModelAppend.GetOutput())
      self.affectedAreaModelNode.SetAndObservePolyData(affectedBallAreaAppend.GetOutput())

    """
    Show segmentations
    """
    if not self.segmentationEditorShow3DButton.isChecked() == checked:
      self.segmentationEditorShow3DButton.checked = checked
    if self.session.data.segmentModelNode:
      if not self.session.data.segmentModelNode.GetDisplayNode().GetVisibility() == checked:
        self.session.data.segmentModelNode.GetDisplayNode().SetVisibility(checked)
    pass  

  @vtk.calldata_type(vtk.VTK_STRING)
  def onInitiateTargeting(self, caller, event, callData):
    self._initiateTargeting(ast.literal_eval(callData))

  def _initiateTargeting(self, retryMode=False):
    self.resetAndInitialize()
    self.session.retryMode = retryMode
    if self.session.seriesTypeManager.isCoverProstate(self.session.currentSeries):
      if self.session.data.usePreopData:
        if self.session.retryMode:
          if not self.loadLatestCoverProstateResultData():
            self.loadInitialData()
        else:
          self.loadInitialData()
      else:
        self.session.movingVolume = self.session.currentSeriesVolume
    else:
      self.loadLatestCoverProstateResultData()
    self.active = True

  def loadInitialData(self):
    self.session.movingLabel = self.session.data.initialLabel
    self.session.movingVolume = self.session.data.initialVolume
    self.session.movingTargets = self.session.data.initialTargets

  def onActivation(self):
    self.session.fixedVolume = self.session.currentSeriesVolume
    if not self.session.fixedVolume:
      return
    self.updateAvailableLayouts()
    self.setupFourUpView(self.session.currentSeriesVolume)
    self.segmentationEditor.setSegmentationNode(self.segmentModelNode)
    self.segmentationEditor.setMasterVolumeNode(self.session.currentSeriesVolume)
    super(ProstateCryoAblationTargetingStep, self).onActivation()

  def updateAvailableLayouts(self):
    pass

  def onDeactivation(self):
    super(ProstateCryoAblationTargetingStep, self).onDeactivation()


  def loadLatestCoverProstateResultData(self):
    coverProstate = self.session.data.getMostRecentApprovedCoverProstateRegistration()
    if coverProstate:
      self.session.movingVolume = coverProstate.volumes.fixed
      self.session.movingLabel = coverProstate.labels.fixed
      self.session.movingTargets = coverProstate.targets.approved
      return True
    return False

  def addSessionObservers(self):
    super(ProstateCryoAblationTargetingStep, self).addSessionObservers()
    self.session.addEventObserver(self.session.InitiateTargetingEvent, self.onInitiateTargeting)

  def removeSessionEventObservers(self):
    super(ProstateCryoAblationTargetingStep, self).removeSessionEventObservers()
    self.session.removeEventObserver(self.session.InitiateTargetingEvent, self.onInitiateTargeting)


  @vtk.calldata_type(vtk.VTK_STRING)
  def onNewImageSeriesReceived(self, caller, event, callData):
    # TODO: control here to automatically activate the step
    if not self.active:
      return
    newImageSeries = ast.literal_eval(callData)
    for series in reversed(newImageSeries):
      if self.session.seriesTypeManager.isCoverProstate(series):
        if series != self.session.currentSeries:
          if not slicer.util.confirmYesNoDisplay("Another %s was received. Do you want to use this one?"
                                                  % self.getSetting("COVER_PROSTATE")):
            return
          self.session.currentSeries = series
          self._initiateTargeting()
          self.onActivation()
          return


  def onTargetingStarted(self, caller, event):
    if self.showAffectiveZoneButton.isChecked():
      self.showAffectiveZoneButton.click()
    if self.targetingPlugin.targetTablePlugin.currentTargets:
      self.targetingPlugin.targetTablePlugin.currentTargets.SetLocked(False)
    self.backButton.enabled = False
    pass

  def onTargetingFinished(self, caller, event):
    self.targetingPlugin.targetTablePlugin.currentTargets.SetLocked(True)
    self.finishStepButton.enabled = True
    self.backButton.enabled = True
    pass