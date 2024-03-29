# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

set(libraryTargetName iotfleetwise.offboardconnectivityawsiot)

# The alias name is what other targets will use as a dependency
set(libraryAliasName IoTFleetWise::OffboardConnectivityAwsIot)

set(librarySrc
  src/AwsIotChannel.cpp
  src/AwsIotConnectivityModule.cpp
  src/PayloadManager.cpp
  src/RemoteProfiler.cpp)

add_library(
  ${libraryTargetName}
  # STATIC or SHARED left out to depend on BUILD_SHARED_LIBS
  ${librarySrc}
)

find_path(JSONCPP_INCLUDE_DIR "json/json.h" PATH_SUFFIXES "jsoncpp")
find_library(JSONCPP_LIBRARY NAMES jsoncpp)

set(OLD_BUILD_SHARED_LIBS ${BUILD_SHARED_LIBS})
set(BUILD_SHARED_LIBS ${FWE_IOT_SDK_SHARED_LIBS})
find_package(aws-crt-cpp REQUIRED)
find_package(GreengrassIpc-cpp REQUIRED)
set(BUILD_SHARED_LIBS ${OLD_BUILD_SHARED_LIBS})

message(STATUS "Connectivity json include ${JSONCPP_INCLUDE_DIR}")
target_include_directories(${libraryTargetName} PUBLIC include
${JSONCPP_INCLUDE_DIR})


target_link_libraries(
  ${libraryTargetName}
  IoTFleetWise::OffboardConnectivity
  IoTFleetWise::Platform
  AWS::aws-crt-cpp
  AWS::GreengrassIpc-cpp
  ${SNAPPY_LIBRARIES}
  ${JSONCPP_LIBRARY}
)


add_library(${libraryAliasName} ALIAS ${libraryTargetName})
