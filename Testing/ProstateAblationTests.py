import unittest
import os, inspect, slicer
from ProstateAblationUtils.session import ProstateAblationSession
from ProstateAblationUtils.sessionData import SessionData

__all__ = ['ProstateAblationSessionTests', 'RegistrationResultsTest']

tempDir =  os.path.join(slicer.app.temporaryPath, "ProstateAblationSessionResults")

class ProstateAblationSessionTests(unittest.TestCase):

  @classmethod
  def setUpClass(cls):
    cls.session = ProstateAblationSession()

  def runTest(self):
    self.test_ProstateAblationSessionEvents()
    self.test_ProstateAblationSessionSingleton()

  def test_ProstateAblationSessionEvents(self):
    self.directoryChangedEventCalled = False
    self.session.addEventObserver(self.session.DirectoryChangedEvent,
                                  lambda event,caller:setattr(self, "directoryChangedEventCalled", True))

    self.assertFalse(self.directoryChangedEventCalled)
    self.session.directory = tempDir
    self.assertTrue(self.directoryChangedEventCalled)

  def test_ProstateAblationSessionSingleton(self):
    session = ProstateAblationSession()
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