import ConfigParser
import inspect, os
from SlicerDevelopmentToolboxUtils.mixins import ModuleWidgetMixin
from constants import ProstateCryoAblationConstants

class ConfigurationParser(ModuleWidgetMixin):

  SEPERATOR = ", "

  def __init__(self, configFile):
    self.moduleName = ProstateCryoAblationConstants.MODULE_NAME
    self.configFile = configFile
    self.loadConfiguration()

  def setTupleSetting(self, key, stringValue):
    valueList = stringValue.split(self.SEPERATOR)
    self.setSetting(key, valueList)

  def getTupleSetting(self, key):
    stringValue = self.getSetting(key)
    if type(stringValue) == type(tuple()):
      return stringValue
    elif type(stringValue) == type(str()):
      return tuple(stringValue.split(self.SEPERATOR))
    return None

  def convertToTuple(self, stringValue):
    return tuple(stringValue.split(self.SEPERATOR))

  def loadConfiguration(self):
    self.config = ConfigParser.RawConfigParser()
    self.config.read(self.configFile)
    if not self.getSetting("ZFrame_Registration_Class_Name"):
      self.setSetting("ZFrame_Registration_Class_Name", self.config.get('ZFrame Registration', 'class'))
    if not self.getTupleSetting("COVER_PROSTATE") or \
      (not self.convertToTuple(self.config.get('Series Descriptions', 'COVER_PROSTATE')) == self.getTupleSetting("COVER_PROSTATE")):
      self.setTupleSetting("COVER_PROSTATE", self.config.get('Series Descriptions', 'COVER_PROSTATE'))
    if not self.getTupleSetting("COVER_TEMPLATE") or \
      (not self.convertToTuple(self.config.get('Series Descriptions', 'COVER_TEMPLATE')) == self.getTupleSetting("COVER_TEMPLATE")):
      self.setTupleSetting("COVER_TEMPLATE", self.config.get('Series Descriptions', 'COVER_TEMPLATE'))
    if not self.getTupleSetting("NEEDLE_IMAGE") or \
      (not self.convertToTuple(self.config.get('Series Descriptions', 'NEEDLE_IMAGE')) == self.getTupleSetting("NEEDLE_IMAGE")):
      self.setTupleSetting("NEEDLE_IMAGE", self.config.get('Series Descriptions', 'NEEDLE_IMAGE'))
    if not self.getTupleSetting("VIBE_IMAGE") or \
      (not self.convertToTuple(self.config.get('Series Descriptions', 'VIBE_IMAGE')) == self.getTupleSetting("VIBE_IMAGE")):
      self.setTupleSetting("VIBE_IMAGE", self.config.get('Series Descriptions', 'VIBE_IMAGE'))
    if not self.getTupleSetting("OTHER_IMAGE") or \
      (not self.convertToTuple(self.config.get('Series Descriptions', 'OTHER_IMAGE')) == self.getTupleSetting("OTHER_IMAGE")):
      self.setTupleSetting("OTHER_IMAGE", self.config.get('Series Descriptions', 'OTHER_IMAGE'))

    tupleList = tuple()
    for x in ['COVER_TEMPLATE', 'COVER_PROSTATE', 'NEEDLE_IMAGE']:
      tupleList += self.convertToTuple(self.config.get('Series Descriptions', x))
    self.setSetting("SERIES_TYPES", tupleList)

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



