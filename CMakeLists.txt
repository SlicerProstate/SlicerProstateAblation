cmake_minimum_required(VERSION 3.5)

project(SlicerProstateAblation)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/SlicerProstate/SlicerProstateAblation")
set(EXTENSION_CATEGORY "IGT")
set(EXTENSION_CONTRIBUTORS "Longquan Chen(SPL), Christian Herz(SPL), Junichi Tokuda(SPL)")
set(EXTENSION_DESCRIPTION "This extension provides support for prostate cryoablation.")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/SlicerProstate/SlicerProstateAblation/master/SlicerProstateAblation.png")
set(EXTENSION_SCREENSHOTURLS "https://raw.githubusercontent.com/SlicerProstate/SlicerProstateAblation/master/Screenshots/Slicelet.png")
set(EXTENSION_DEPENDS "SlicerDevelopmentToolbox ZFrameRegistration")

#-----------------------------------------------------------------------------
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

add_subdirectory(ProstateAblation)


#-----------------------------------------------------------------------------
if(BUILD_TESTING)

  # Register the unittest subclass in the main script as a ctest.
  # Note that the test will also be available at runtime.
  # slicer_add_python_unittest(SCRIPT ${MODULE_NAME}.py)

  # Additional build-time testing
  # add_subdirectory(Testing)
endif()

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
