import numpy
import ctk
import vtk
import qt
import logging
from ProstateCryoAblationUtils.constants import ProstateCryoAblationConstants as constants
from SlicerDevelopmentToolboxUtils.decorators import logmethod, onModuleSelected
from ProstateCryoAblationUtils.steps.base import ProstateCryoAblationPlugin, ProstateCryoAblationLogicBase

from SlicerDevelopmentToolboxUtils.helpers import SliceAnnotation


class ProstateCryoAblationRegistrationResultsLogic(ProstateCryoAblationLogicBase):

  def __init__(self):
    super(ProstateCryoAblationRegistrationResultsLogic, self).__init__()


class ProstateCryoAblationRegistrationResultsPlugin(ProstateCryoAblationPlugin):

  LogicClass = ProstateCryoAblationRegistrationResultsLogic
  NAME = "RegistrationResults"

  RegistrationTypeSelectedEvent = vtk.vtkCommand.UserEvent + 657

  @property
  def resultSelectorVisible(self):
    return self._showResultSelector

  @resultSelectorVisible.setter
  def resultSelectorVisible(self, visible):
    self.resultSelector.visible = visible
    self._showResultSelector = visible

  @property
  def registrationTypeButtonsVisible(self):
    return self.registrationTypesGroupBox.visible

  @registrationTypeButtonsVisible.setter
  def registrationTypeButtonsVisible(self, visible):
    self.registrationTypesGroupBox.visible = visible

  @property
  def visualEffectsVisible(self):
    return self.visualEffectsGroupBox.visible

  @visualEffectsVisible.setter
  def visualEffectsVisible(self, visible):
    self.visualEffectsGroupBox.visible = visible

  @property
  def visualEffectsTitle(self):
    return self.visualEffectsGroupBox.title

  @visualEffectsTitle.setter
  def visualEffectsTitle(self, title):
    self.visualEffectsGroupBox.title = title

  @property
  def titleVisible(self):
    return self.registrationResultsGroupBox.title == self._title

  @titleVisible.setter
  def titleVisible(self, visible):
    self.registrationResultsGroupBox.title = self._title if visible else ""

  _title = "Registration Results"

  def __init__(self):
    self._showResultSelector = True
    super(ProstateCryoAblationRegistrationResultsPlugin, self).__init__()

  def cleanup(self):
    self.removeSliceAnnotations()
    self.resetVisualEffects()

  def setupIcons(self):
    self.revealCursorIcon = self.createIcon('icon-revealCursor.png')

  def setup(self):
    super(ProstateCryoAblationRegistrationResultsPlugin, self).setup()
    self.registrationResultsGroupBox = qt.QGroupBox("Registration Results")
    self.registrationResultsGroupBoxLayout = qt.QGridLayout()
    self.registrationResultsGroupBox.setLayout(self.registrationResultsGroupBoxLayout)

    self.resultSelector = ctk.ctkComboBox()
    self.registrationResultsGroupBoxLayout.addWidget(self.resultSelector)

    self.setupRegistrationResultButtons()
    self.setupVisualEffectsUIElements()

    self.registrationResultsGroupBoxLayout.addWidget(self.createHLayout([self.registrationTypesGroupBox,
                                                                         self.visualEffectsGroupBox]))
    self.layout().addWidget(self.registrationResultsGroupBox)

  def setupRegistrationResultButtons(self):
    self.rigidResultButton = self.createButton('Rigid', checkable=True, name='rigid')
    self.affineResultButton = self.createButton('Affine', checkable=True, name='affine')
    self.bSplineResultButton = self.createButton('BSpline', checkable=True, name='bSpline')
    self.registrationButtonGroup = qt.QButtonGroup()
    self.registrationButtonGroup.addButton(self.rigidResultButton, 1)
    self.registrationButtonGroup.addButton(self.affineResultButton, 2)
    self.registrationButtonGroup.addButton(self.bSplineResultButton, 3)

    self.registrationTypesGroupBox = qt.QGroupBox("Type")
    self.registrationTypesGroupBoxLayout = qt.QFormLayout(self.registrationTypesGroupBox)
    self.registrationTypesGroupBoxLayout.addWidget(self.createVLayout([self.rigidResultButton,
                                                                       self.affineResultButton,
                                                                       self.bSplineResultButton]))

  def setRegistrationResultButtonVisibility(self, show):
    self.registrationButtonGroup.visible = show

  def setupVisualEffectsUIElements(self):
    self.setupOpacity()
    self.setupRock()
    self.setupFlicker()

    self.animaHolderLayout = self.createHLayout([self.rockCheckBox, self.flickerCheckBox])
    self.visualEffectsGroupBox = qt.QGroupBox("Visual Effects")
    self.visualEffectsGroupBoxLayout = qt.QFormLayout(self.visualEffectsGroupBox)
    self.revealCursorButton = self.createButton("", icon=self.revealCursorIcon, checkable=True,
                                                toolTip="Use reveal cursor")
    slider = self.createHLayout([self.opacitySpinBox, self.animaHolderLayout])
    self.visualEffectsGroupBoxLayout.addWidget(self.createVLayout([slider, self.revealCursorButton]))

  def setupOpacity(self):
    self.opacitySpinBox = qt.QDoubleSpinBox()
    self.opacitySpinBox.minimum = 0
    self.opacitySpinBox.maximum = 1.0
    self.opacitySpinBox.value = 0
    self.opacitySpinBox.singleStep = 0.05
    self.opacitySliderPopup = ctk.ctkPopupWidget(self.opacitySpinBox)
    popupLayout = qt.QHBoxLayout(self.opacitySliderPopup)

    self.opacitySlider = ctk.ctkDoubleSlider(self.opacitySliderPopup)
    self.opacitySlider.orientation = qt.Qt.Horizontal
    self.opacitySlider.minimum = 0
    self.opacitySlider.maximum = 1.0
    self.opacitySlider.value = 0
    self.opacitySlider.singleStep = 0.05
    popupLayout.addWidget(self.opacitySlider)
    self.opacitySliderPopup.verticalDirection = ctk.ctkBasePopupWidget.TopToBottom
    self.opacitySliderPopup.animationEffect = ctk.ctkBasePopupWidget.FadeEffect
    self.opacitySliderPopup.orientation = qt.Qt.Horizontal
    self.opacitySliderPopup.easingCurve = qt.QEasingCurve.OutQuart
    self.opacitySliderPopup.effectDuration = 100

  def setupRock(self):
    self.rockCount = 0
    self.rockTimer = self.createTimer(50, self.onRockToggled, singleShot=False)
    self.rockCheckBox = qt.QCheckBox("Rock")
    self.rockCheckBox.checked = False

  def setupFlicker(self):
    self.flickerTimer = self.createTimer(400, self.onFlickerToggled, singleShot=False)
    self.flickerCheckBox = qt.QCheckBox("Flicker")
    self.flickerCheckBox.checked = False

  def setupConnections(self):
    self.registrationButtonGroup.connect('buttonClicked(QAbstractButton*)', self.onRegistrationButtonChecked)
    self.resultSelector.connect('currentIndexChanged(QString)', self.onRegistrationResultSelected)
    self.revealCursorButton.connect('toggled(bool)', self.onRevealToggled)
    self.rockCheckBox.connect('toggled(bool)', self.onRockToggled)
    self.flickerCheckBox.connect('toggled(bool)', self.onFlickerToggled)
    self.opacitySpinBox.valueChanged.connect(self.onOpacitySpinBoxChanged)
    self.opacitySlider.valueChanged.connect(self.onOpacitySliderChanged)

  def show(self):
    qt.QWidget.show(self)
    self.onActivation()

  def hide(self):
    qt.QWidget.hide(self)
    self.onDeactivation()

  @logmethod(logging.INFO)
  def onActivation(self):
    super(ProstateCryoAblationRegistrationResultsPlugin, self).onActivation()
    if not self.currentResult:
      return
    self.updateRegistrationResultSelector()
    self.onCurrentResultChanged()
    defaultLayout = self.getSetting("DEFAULT_EVALUATION_LAYOUT")
    self.onLayoutChanged(getattr(constants, defaultLayout, constants.LAYOUT_SIDE_BY_SIDE))

  def onDeactivation(self):
    super(ProstateCryoAblationRegistrationResultsPlugin, self).onDeactivation()
    self.cleanup()

  @vtk.calldata_type(vtk.VTK_STRING)
  def onCaseClosed(self, caller, event, callData):
    self.cleanup()

  @logmethod(logging.INFO)
  def onCurrentResultChanged(self, caller=None, event=None):
    if not self.active:
      return
    if not self.currentResult or self.currentResult.skipped:
      return self.onNoResultAvailable()
    if self.currentResult.approved or self.currentResult.rejected:
      return self.onResultApprovedOrRejected()
    self.setAvailableLayouts([constants.LAYOUT_FOUR_UP, constants.LAYOUT_SIDE_BY_SIDE])

  def onResultApprovedOrRejected(self):
    if self.session.seriesTypeManager.isCoverProstate(self.currentResult.name) and not self.session.data.usePreopData:
      self.onNoResultAvailable()
    else:
      self.setAvailableLayouts([constants.LAYOUT_FOUR_UP, constants.LAYOUT_SIDE_BY_SIDE if
                                self.currentResult.volumes.moving else constants.LAYOUT_RED_SLICE_ONLY])
      self.layoutManager.setLayout(constants.LAYOUT_SIDE_BY_SIDE)

  def onNoResultAvailable(self):
    self.setAvailableLayouts([constants.LAYOUT_RED_SLICE_ONLY, constants.LAYOUT_FOUR_UP])
    self.setupRedSlicePreview(self.session.currentSeries)

  @onModuleSelected("ProstateCryoAblation")
  def onLayoutChanged(self, layout=None):
    self.removeSliceAnnotations()
    if not self.currentResult:
      return
    self.setupRegistrationResultView(layout)
    self.onRegistrationResultSelected(self.currentResult.name)
    self.onOpacitySpinBoxChanged(self.opacitySpinBox.value)

  def onRegistrationButtonChecked(self, button):
    self.displayRegistrationResultsByType(button.name)

  def onOpacitySpinBoxChanged(self, value):
    if self.opacitySlider.value != value:
      self.opacitySlider.value = value
    self.onOpacityChanged(value)

  def onOpacitySliderChanged(self, value):
    if self.opacitySpinBox.value != value:
      self.opacitySpinBox.value = value

  def onOpacityChanged(self, value):
    if self.layoutManager.layout == constants.LAYOUT_FOUR_UP:
      self.redCompositeNode.SetForegroundOpacity(value)
      self.greenCompositeNode.SetForegroundOpacity(value)
    self.yellowCompositeNode.SetForegroundOpacity(value)
    self.setOldNewIndicatorAnnotationOpacity(value)

  def onRockToggled(self):
    self.updateRevealCursorAvailability()
    if self.rockCheckBox.checked:
      self.startRocking()
    else:
      self.stopRocking()

  def onFlickerToggled(self):
    self.updateRevealCursorAvailability()
    if self.flickerCheckBox.checked:
      self.startFlickering()
    else:
      self.stopFlickering()

  def onRevealToggled(self, checked):
    self.revealCursor = getattr(self, "revealCursor", None)
    if self.revealCursor:
      self.revealCursor.tearDown()
    if checked:
      import CompareVolumes
      self.revealCursor = CompareVolumes.LayerReveal()

  def onRegistrationResultSelected(self, seriesText, registrationType=None):
    self.currentResult = seriesText
    if self.currentResult.skipped:
      return self.setupSkippedRegistrationResultSliceViews()
    elif registrationType:
      return self.checkButtonByRegistrationType(registrationType)
    elif self.currentResult.approved:
      return self.displayApprovedRegistrationResults()
    elif self.registrationButtonGroup.checkedId() != -1:
      return self.onRegistrationButtonChecked(self.registrationButtonGroup.checkedButton())
    self.bSplineResultButton.click()

  def displayApprovedRegistrationResults(self):
    self.displayRegistrationResults(self.currentResult.targets.approved, self.currentResult.registrationType)

  def displayRegistrationResultsByType(self, registrationType):
    self.displayRegistrationResults(self.currentResult.getTargets(registrationType), registrationType)
    self.invokeEvent(self.RegistrationTypeSelectedEvent, registrationType)

  def displayRegistrationResults(self, targets, registrationType):
    self.hideAllFiducialNodes()
    self.showIntraopTargets(targets)
    self.setPreopTargetVisibility()
    self.setupRegistrationResultSliceViews(registrationType)

  def showIntraopTargets(self, targets):
    self.setupTargetViewNodes(targets)
    self.session.applyDefaultTargetDisplayNode(targets)
    self.setFiducialNodeVisibility(targets)

  def startRocking(self):
    if self.flickerCheckBox.checked:
      self.flickerCheckBox.checked = False
    self.rockTimer.start()
    self.opacitySpinBox.value = 0.5 + numpy.sin(self.rockCount / 10.) / 2.
    self.rockCount += 1

  def stopRocking(self):
    self.rockTimer.stop()
    self.opacitySpinBox.value = 1.0

  def startFlickering(self):
    if self.rockCheckBox.checked:
      self.rockCheckBox.checked = False
    self.flickerTimer.start()
    self.opacitySpinBox.value = 1.0 if self.opacitySpinBox.value == 0.0 else 0.0

  def stopFlickering(self):
    self.flickerTimer.stop()
    self.opacitySpinBox.value = 1.0

  def resetVisualEffects(self):
    self.flickerCheckBox.checked = False
    self.rockCheckBox.checked = False
    self.revealCursorButton.checked = False

  def setOldNewIndicatorAnnotationOpacity(self, value):
    self.newImageAnnotation = getattr(self, "newImageAnnotation", None)
    if self.newImageAnnotation:
      self.newImageAnnotation.opacity = value

    self.oldImageAnnotation = getattr(self, "oldImageAnnotation", None)
    if self.oldImageAnnotation:
      self.oldImageAnnotation.opacity = 1.0 - value

  def updateRevealCursorAvailability(self):
    self.revealCursorButton.checked = False
    self.revealCursorButton.enabled = not (self.rockCheckBox.checked or self.flickerCheckBox.checked)

  def updateRegistrationResultSelector(self):
    resultName = self.currentResult.name
    self.resultSelector.blockSignals(True)
    self.resultSelector.clear()
    for result in self.session.data.getResultsBySeriesNumber(self.currentResult.seriesNumber):
      self.resultSelector.addItem(result.name)
    if self._showResultSelector:
      self.resultSelector.visible = self.resultSelector.model().rowCount() > 1
    self.resultSelector.blockSignals(False)
    self.resultSelector.currentIndex = self.resultSelector.findText(resultName, qt.Qt.MatchExactly)

  def checkButtonByRegistrationType(self, registrationType):
    next((b for b in self.registrationButtonGroup.buttons() if b.name == registrationType), None).click()
    # self.selectLastSelectedTarget()

  def setPreopTargetVisibility(self):
    self.refreshViewNodeIDs(self.session.data.initialTargets, [self.redSliceNode])
    self.setFiducialNodeVisibility(self.session.data.initialTargets,
                                    show=self.layoutManager.layout == constants.LAYOUT_SIDE_BY_SIDE)

  def setupSkippedRegistrationResultSliceViews(self):
    self.setBackgroundToVolumeID(self.currentResult.volumes.fixed.GetID())

  def setupRegistrationResultSliceViews(self, registrationType):
    self.configureRedCompositeNodeForCurrentLayout()
    self.configureCompositeNodesForCurrentLayout(registrationType)
    self.setOrientationForCurrentLayout()
    # self.centerViewsToProstate()

  def setOrientationForCurrentLayout(self):
    self.setDefaultOrientation()
    if self.layoutManager.layout == constants.LAYOUT_SIDE_BY_SIDE:
      self.setAxialOrientation()

  def configureCompositeNodesForCurrentLayout(self, registrationType):
    compositeNodes = self.getCompositeNodesForCurrentLayout()
    bgVolume = self.currentResult.getVolume(registrationType)
    bgVolume = bgVolume if bgVolume and self.logic.isVolumeExtentValid(bgVolume) else self.currentResult.volumes.fixed
    for compositeNode in compositeNodes:
      compositeNode.SetForegroundVolumeID(self.currentResult.volumes.fixed.GetID())
      compositeNode.SetBackgroundVolumeID(bgVolume.GetID())

  def getCompositeNodesForCurrentLayout(self):
    if self.layoutManager.layout == constants.LAYOUT_SIDE_BY_SIDE:
      return [self.yellowCompositeNode]
    elif self.layoutManager.layout == constants.LAYOUT_FOUR_UP:
      return [self.redCompositeNode, self.yellowCompositeNode, self.greenCompositeNode]
    return []

  def configureRedCompositeNodeForCurrentLayout(self):
    if self.layoutManager.layout in [constants.LAYOUT_SIDE_BY_SIDE, constants.LAYOUT_RED_SLICE_ONLY]:
      self.redCompositeNode.SetForegroundVolumeID(None)
      self.redCompositeNode.SetBackgroundVolumeID(self.session.data.initialVolume.GetID())

  def setupRegistrationResultView(self, layout=None):
    if layout:
      self.layoutManager.setLayout(layout)
    self.hideAllLabels()
    self.addSliceAnnotations()

  def addSliceAnnotations(self):
    if self.layoutManager.layout == constants.LAYOUT_FOUR_UP:
      self.addFourUpSliceAnnotations()
      self.setDefaultOrientation()
    else:
      if self.layoutManager.layout == constants.LAYOUT_SIDE_BY_SIDE:
        self.addSideBySideSliceAnnotations()
      elif self.layoutManager.layout == constants.LAYOUT_RED_SLICE_ONLY:
        self.addRedOnlySliceAnnotations()
      self.setAxialOrientation()

  def removeSliceAnnotations(self):
    self.sliceAnnotations = getattr(self, "sliceAnnotations", [])
    for annotation in self.sliceAnnotations:
      annotation.remove()
    self.sliceAnnotations = []
    self.newImageAnnotation = None
    self.oldImageAnnotation = None

  def addSideBySideSliceAnnotations(self):
    self.removeSliceAnnotations()
    kwargs = {"yPos":55, "fontSize":30}
    self.sliceAnnotations.append(SliceAnnotation(self.redWidget, constants.LEFT_VIEWER_SLICE_ANNOTATION_TEXT, **kwargs))
    self.sliceAnnotations.append(SliceAnnotation(self.yellowWidget, constants.RIGHT_VIEWER_SLICE_ANNOTATION_TEXT, **kwargs))
    self.addNewImageAnnotation(self.yellowWidget, constants.RIGHT_VIEWER_SLICE_NEEDLE_IMAGE_ANNOTATION_TEXT)
    self.addOldImageAnnotation(self.yellowWidget, constants.RIGHT_VIEWER_SLICE_TRANSFORMED_ANNOTATION_TEXT)
    self.addRegistrationResultStatusAnnotation(self.yellowWidget)

  def addFourUpSliceAnnotations(self):
    self.removeSliceAnnotations()
    if not (self.currentResult.skipped or (self.session.seriesTypeManager.isCoverProstate(self.currentResult.name) and
                                             not self.session.data.usePreopData)):
      self.sliceAnnotations.append(SliceAnnotation(self.redWidget, constants.RIGHT_VIEWER_SLICE_ANNOTATION_TEXT,
                                                   yPos=50, fontSize=20))
      self.addNewImageAnnotation(self.redWidget, constants.RIGHT_VIEWER_SLICE_NEEDLE_IMAGE_ANNOTATION_TEXT, fontSize=15)
      self.addOldImageAnnotation(self.redWidget, constants.RIGHT_VIEWER_SLICE_TRANSFORMED_ANNOTATION_TEXT, fontSize=15)
    self.addRegistrationResultStatusAnnotation(self.redWidget)

  def addRedOnlySliceAnnotations(self):
    self.removeSliceAnnotations()
    self.addRegistrationResultStatusAnnotation(self.redWidget)

  def addNewImageAnnotation(self, widget, text, fontSize=20):
    self.newImageAnnotation = SliceAnnotation(widget, text, yPos=35, opacity=0.0, color=(0, 0.5, 0), fontSize=fontSize)
    self.sliceAnnotations.append(self.newImageAnnotation)

  def addOldImageAnnotation(self, widget, text, fontSize=20):
    self.oldImageAnnotation = SliceAnnotation(widget, text, yPos=35, fontSize=fontSize)
    self.sliceAnnotations.append(self.oldImageAnnotation)

  def addRegistrationResultStatusAnnotation(self, widget):
    annotationText = None
    if self.currentResult.approved:
      annotationText = constants.APPROVED_RESULT_TEXT_ANNOTATION
    elif self.currentResult.rejected:
      annotationText = constants.REJECTED_RESULT_TEXT_ANNOTATION
    elif self.currentResult.skipped:
      annotationText = constants.SKIPPED_RESULT_TEXT_ANNOTATION
    if annotationText:
      self.sliceAnnotations.append(SliceAnnotation(widget, annotationText, fontSize=15, yPos=20))

  def setupTargetViewNodes(self, targetNode):
    sliceNodes = [self.yellowSliceNode]
    if self.layoutManager.layout == constants.LAYOUT_RED_SLICE_ONLY:
      sliceNodes = [self.redSliceNode]
    elif self.layoutManager.layout == constants.LAYOUT_FOUR_UP:
      sliceNodes = [self.redSliceNode, self.yellowSliceNode, self.greenSliceNode]
    self.refreshViewNodeIDs(targetNode, sliceNodes)
    targetNode.SetLocked(True)