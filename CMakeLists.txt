cmake_minimum_required(VERSION 3.5)

project(ProstateCryoAblation)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://github.com/SlicerProstate/SlicerCryoAblation")
set(EXTENSION_CATEGORY "IGT")
set(EXTENSION_CONTRIBUTORS "Longquan Chen(SPL), Christian Herz(SPL), Junichi Tokuda(SPL)")
set(EXTENSION_DESCRIPTION "This extension provides support for prostate cryoablation.")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/SlicerProstate/SlicerCryoAblation/master/ProstateCryoAblation.png")
set(EXTENSION_SCREENSHOTURLS "https://raw.githubusercontent.com/SlicerProstate/SlicerCryoAblation/master/Screenshots/1.png https://raw.githubusercontent.com/SlicerProstate/SlicerCryoAblation/master/Screenshots/2.png")
set(EXTENSION_DEPENDS "SlicerDevelopmentToolbox SlicerZFrameRegistration")

#-----------------------------------------------------------------------------
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

add_subdirectory(ProstateCryoAblation)


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
