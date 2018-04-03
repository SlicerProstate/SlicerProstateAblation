cmake_minimum_required(VERSION 2.8.9)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_NAME ProstateCryoAblation)
set(EXTENSION_HOMEPAGE "https://github.com/leochan2009/ProstateCryoAblation")
set(EXTENSION_CATEGORY "IGT")
set(EXTENSION_CONTRIBUTORS "Longquan Chen(SPL)")
set(EXTENSION_DESCRIPTION "This extension provides support for prostate cryoablation.")
#set(EXTENSION_ICONURL "http://wiki.slicer.org/slicerWiki")
#set(EXTENSION_SCREENSHOTURLS "http://wiki.slicer.org/slicerWiki")
set(EXTENSION_STATUS "alpha")
set(EXTENSION_DEPENDS "SlicerDevelopmentToolbox, SliceTracker")

#-----------------------------------------------------------------------------
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

add_subdirectory(ProstateCryoAblation)
#add_subdirectory(ZFrameCalibration)


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
