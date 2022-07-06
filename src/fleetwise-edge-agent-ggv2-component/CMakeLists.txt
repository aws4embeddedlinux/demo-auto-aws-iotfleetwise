cmake_minimum_required(VERSION 3.10.2)

project(fwe-gg VERSION 0.1.0)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

set(FWE_BUILD_DOC OFF CACHE BOOL "")
set(FWE_BUILD_CONNECTIVITY OFF CACHE BOOL "")
set(BUILD_TESTING OFF CACHE BOOL "")

include(lib/aws-iot-fleetwise-edge/cmake/compiler_gcc.cmake)

add_subdirectory(lib/aws-iot-fleetwise-edge)
add_subdirectory(src/offboardconnectivity)
