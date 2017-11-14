import unittest
import os, inspect, slicer
from ProstateCryoAblationUtils.session import ProstateCryoAblationSession
from ProstateCryoAblationUtils.sessionData import SessionData

__all__ = ['ProstateCryoAblationSessionTests', 'RegistrationResultsTest']

tempDir =  os.path.join(slicer.app.temporaryPath, "ProstateCryoAblationSessionResults")

class ProstateCryoAblationSessionTests(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    cls.session = ProstateCryoAblationSession()

  def runTest(self):
    self.test_ProstateCryoAblationSessionEvents()
    self.test_ProstateCryoAblationSessionSingleton()

  def test_ProstateCryoAblationSessionEvents(self):
    self.directoryChangedEventCalled = False
    self.session.addEventObserver(self.session.DirectoryChangedEvent,
                                  lambda event,caller:setattr(self, "directoryChangedEventCalled", True))

    self.assertFalse(self.directoryChangedEventCalled)
    self.session.directory = tempDir
    self.assertTrue(self.directoryChangedEventCalled)

  def test_ProstateCryoAblationSessionSingleton(self):
    session = ProstateCryoAblationSession()
    self.assertTrue(self.session is session)
    self.assertTrue(session.directory == self.session.directory)


class RegistrationResultsTest(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    cls.registrationResults = SessionData()

  def runTest(self):
    self.test_Reading_json()
    self.test_Writing_json()

  def test_Reading_json(self):
    directory = os.path.join(os.path.dirname(inspect.getfile(self.__class__)), "..", "doc")
    inputFileName = os.path.join(directory, "output_example.json")
    self.registrationResults.load(inputFileName)

  def test_Writing_json(self):
    self.registrationResults.resumed = True
    self.registrationResults.completed = True
    self.registrationResults.save(tempDir)