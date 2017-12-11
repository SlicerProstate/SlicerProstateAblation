import ConfigParser
import inspect, os
from SlicerDevelopmentToolboxUtils.mixins import ModuleWidgetMixin
from constants import ProstateCryoAblationConstants

class ConfigurationParser(ModuleWidgetMixin):

  def __init__(self, configFile):
    self.moduleName = ProstateCryoAblationConstants.MODULE_NAME
    self.configFile = configFile
    self.loadConfiguration()

  def setListSetting(self, key, stringValue):
    listSeries = stringValue.split(', ')
    self.setSetting(key, listSeries)

  def loadConfiguration(self):
    self.config = ConfigParser.RawConfigParser()
    self.config.read(self.configFile)
    if not self.getSetting("ZFrame_Registration_Class_Name"):
      self.setListSetting("ZFrame_Registration_Class_Name", self.config.get('ZFrame Registration', 'class'))
    if not self.getSetting("COVER_PROSTATE") or \
      (not self.config.get('Series Descriptions', 'COVER_PROSTATE') == self.getSetting("COVER_PROSTATE")):
      self.setListSetting("COVER_PROSTATE", self.config.get('Series Descriptions', 'COVER_PROSTATE'))
    if not self.getSetting("COVER_TEMPLATE") or \
      (not self.config.get('Series Descriptions', 'COVER_TEMPLATE') == self.getSetting("COVER_TEMPLATE")):
      self.setListSetting("COVER_TEMPLATE", self.config.get('Series Descriptions', 'COVER_TEMPLATE'))
    if not self.getSetting("NEEDLE_IMAGE") or \
      (not self.config.get('Series Descriptions', 'NEEDLE_IMAGE') == self.getSetting("NEEDLE_IMAGE")):
      self.setListSetting("NEEDLE_IMAGE", self.config.get('Series Descriptions', 'NEEDLE_IMAGE'))
    if not self.getSetting("VIBE_IMAGE") or \
      (not self.config.get('Series Descriptions', 'VIBE_IMAGE') == self.getSetting("VIBE_IMAGE")):
      self.setListSetting("VIBE_IMAGE", self.config.get('Series Descriptions', 'VIBE_IMAGE'))
    if not self.getSetting("OTHER_IMAGE") or \
      (not self.config.get('Series Descriptions', 'OTHER_IMAGE') == self.getSetting("OTHER_IMAGE")):
      self.setListSetting("OTHER_IMAGE", self.config.get('Series Descriptions', 'OTHER_IMAGE'))

    if not self.getSetting("SERIES_TYPES"):
      seriesTypes = [self.config.get('Series Descriptions',x) for x in ['COVER_TEMPLATE', 'COVER_PROSTATE','NEEDLE_IMAGE','VIBE_IMAGE', 'OTHER_IMAGE']]
      self.setSetting("SERIES_TYPES", seriesTypes)

    colorFileName = self.config.get('Color File', 'FileName')
    colorFileFullName = os.path.join(os.path.dirname(inspect.getfile(self.__class__)),
                 '../Resources/Colors', colorFileName)
    if not self.getSetting("Color_File_Name") or not os.path.exists(self.getSetting("Color_File_Name")) \
        or not colorFileFullName == self.getSetting("Color_File_Name"):
      self.setSetting("Color_File_Name", colorFileFullName)


    if not self.getSetting("DEFAULT_EVALUATION_LAYOUT") or \
        (not self.config.get('Evaluation', 'Default_Layout') == self.getSetting("DEFAULT_EVALUATION_LAYOUT")) :
      self.setSetting("DEFAULT_EVALUATION_LAYOUT", self.config.get('Evaluation', 'Default_Layout'))


    self.setSetting("NeedleRadius_ICESEED", self.config.get('NeedleRadius', 'ICESEED'))
    self.setSetting("NeedleRadius_ICEROD", self.config.get('NeedleRadius', 'ICEROD'))

    if not self.getSetting("NeedleType") or \
        (not self.config.get('CurrentNeedleType', 'NeedleType') == self.getSetting("NeedleType")) :
      self.setSetting("NeedleType", self.config.get('CurrentNeedleType', 'NeedleType'))



