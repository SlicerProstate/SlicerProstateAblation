import ConfigParser
import inspect, os
from SlicerDevelopmentToolboxUtils.mixins import ModuleWidgetMixin

class ConfigurationParser(ModuleWidgetMixin):

  def __init__(self, configFile):
    self.moduleName = "ProstateCryoAblation"
    self.configFile = configFile
    self.loadConfiguration()

  def loadConfiguration(self):

    config = ConfigParser.RawConfigParser()
    config.read(self.configFile)

    if not self.getSetting("ZFrame_Registration_Class_Name"):
      self.setSetting("ZFrame_Registration_Class_Name", config.get('ZFrame Registration', 'class'))

    if not self.getSetting("COVER_PROSTATE"):
      self.setSetting("COVER_PROSTATE", config.get('Series Descriptions', 'COVER_PROSTATE'))
    if not self.getSetting("COVER_TEMPLATE"):
      self.setSetting("COVER_TEMPLATE", config.get('Series Descriptions', 'COVER_TEMPLATE'))
    if not self.getSetting("OTHER_IMAGE"):
      self.setSetting("OTHER_IMAGE", config.get('Series Descriptions', 'OTHER_IMAGE'))

    if not self.getSetting("SERIES_TYPES"):
      seriesTypes = [config.get('Series Descriptions',x) for x in ['COVER_TEMPLATE', 'COVER_PROSTATE', 'OTHER_IMAGE']]
      self.setSetting("SERIES_TYPES", seriesTypes)
