from SlicerDevelopmentToolboxUtils.buttons import LayoutButton, CheckableIconButton, BasicIconButton
import os
import qt
import slicer

class ScreenShotButton(BasicIconButton):
  parentDir = os.path.normpath(os.path.dirname(os.path.realpath(__file__)))
  grandParentDir = os.path.normpath(os.path.dirname(parentDir))
  grandGrandParentDir = os.path.normpath(os.path.dirname(grandParentDir))
  grandGrandGrandParentDir = os.path.normpath(os.path.dirname(grandGrandParentDir))
  iconFileName = os.path.join(grandGrandGrandParentDir, 'Resources', 'Icons', 'screenShot.png')
  _ICON = qt.QIcon(iconFileName)

  @property
  def caseResultDir(self):
    return self._caseResultDir

  @caseResultDir.setter
  def caseResultDir(self, value):
    self._caseResultDir = value
    self.imageIndex = 0

  def __init__(self, text="", parent=None, **kwargs):
    super(ScreenShotButton, self).__init__(text, parent, **kwargs)
    import ScreenCapture
    self.cap = ScreenCapture.ScreenCaptureLogic()
    self.checkable = False
    self._caseResultDir = ""
    self.imageIndex = 0

  def _connectSignals(self):
    super(ScreenShotButton, self)._connectSignals()
    self.clicked.connect(self.onClicked)

  def onClicked(self):
    if self.caseResultDir:
      self.cap.showViewControllers(False)
      fileName = os.path.join(self._caseResultDir, 'screenShot' + str(self.imageIndex) + '.png')
      if os.path.exists(fileName):
        self.imageIndex = self.imageIndex + 1
        fileName = os.path.join(self._caseResultDir, 'screenShot' + str(self.imageIndex) + '.png')
      self.cap.captureImageFromView(None, fileName)
      self.cap.showViewControllers(True)
      self.imageIndex = self.imageIndex + 1
    else:
      slicer.util.warningDisplay("Case was not created, create a case first")
    pass