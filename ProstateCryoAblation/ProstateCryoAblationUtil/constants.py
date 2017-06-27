import slicer
from SlicerDevelopmentToolboxUtils.mixins import ModuleWidgetMixin as helper
from SliceTrackerUtils.constants import SliceTrackerConstants

class ProstateCryoAblationConstants(SliceTrackerConstants):

  def __init__(self, parent=None):
    super(ProstateCryoAblationConstants, self).__init__(parent)
    MODULE_NAME = "ProstateCryoAblation"
