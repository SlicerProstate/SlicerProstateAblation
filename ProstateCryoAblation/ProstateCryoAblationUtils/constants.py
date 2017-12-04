import slicer

class ProstateCryoAblationConstants(object):

  MODULE_NAME = "ProstateCryoAblation"

  INTRAOP_SAMPLE_DATA_URL = 'https://github.com/SlicerProstate/SliceTracker/releases/download/test-data/Intraop-deid.zip'

  JSON_FILENAME = "results.json"

  LAYOUT_RED_SLICE_ONLY = slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView
  LAYOUT_FOUR_UP = slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView
  LAYOUT_SIDE_BY_SIDE = slicer.vtkMRMLLayoutNode.SlicerLayoutSideBySideView
  ALLOWED_LAYOUTS = [LAYOUT_SIDE_BY_SIDE, LAYOUT_FOUR_UP, LAYOUT_RED_SLICE_ONLY]

  ZFrame_INSTRUCTION_STEPS = {1: "Scroll and click into ZFrame center to set ROI center",
                              2: "Click outside of upper right ZFrame corner to set ROI border"}
