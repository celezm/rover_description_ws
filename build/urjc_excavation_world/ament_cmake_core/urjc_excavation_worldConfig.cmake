# generated from ament/cmake/core/templates/nameConfig.cmake.in

# prevent multiple inclusion
if(_urjc_excavation_world_CONFIG_INCLUDED)
  # ensure to keep the found flag the same
  if(NOT DEFINED urjc_excavation_world_FOUND)
    # explicitly set it to FALSE, otherwise CMake will set it to TRUE
    set(urjc_excavation_world_FOUND FALSE)
  elseif(NOT urjc_excavation_world_FOUND)
    # use separate condition to avoid uninitialized variable warning
    set(urjc_excavation_world_FOUND FALSE)
  endif()
  return()
endif()
set(_urjc_excavation_world_CONFIG_INCLUDED TRUE)

# output package information
if(NOT urjc_excavation_world_FIND_QUIETLY)
  message(STATUS "Found urjc_excavation_world: 1.0.0 (${urjc_excavation_world_DIR})")
endif()

# warn when using a deprecated package
if(NOT "" STREQUAL "")
  set(_msg "Package 'urjc_excavation_world' is deprecated")
  # append custom deprecation text if available
  if(NOT "" STREQUAL "TRUE")
    set(_msg "${_msg} ()")
  endif()
  # optionally quiet the deprecation message
  if(NOT urjc_excavation_world_DEPRECATED_QUIET)
    message(DEPRECATION "${_msg}")
  endif()
endif()

# flag package as ament-based to distinguish it after being find_package()-ed
set(urjc_excavation_world_FOUND_AMENT_PACKAGE TRUE)

# include all config extra files
set(_extras "ament_cmake_export_dependencies-extras.cmake")
foreach(_extra ${_extras})
  include("${urjc_excavation_world_DIR}/${_extra}")
endforeach()
