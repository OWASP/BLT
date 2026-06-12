cmake_minimum_required(VERSION 3.16)
project(SafeCloakChat VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(Qt6 6.4 REQUIRED COMPONENTS Widgets Network)

qt_add_executable(safecloak
    src/main.cpp
    src/Theme.h
    src/SslIdentity.h
    src/SslIdentity.cpp
    src/FramedConnection.h
    src/FramedConnection.cpp
    src/ChatBackend.h
    src/ChatServer.h
    src/ChatServer.cpp
    src/ChatClient.h
    src/ChatClient.cpp
    src/MeshNode.h
    src/MeshNode.cpp
    src/MainWindow.h
    src/MainWindow.cpp
)

target_link_libraries(safecloak PRIVATE Qt6::Widgets Qt6::Network)

option(SAFECLOAK_BUILD_SCREENSHOT_TOOL "Build the offscreen screenshot helper" OFF)
if(SAFECLOAK_BUILD_SCREENSHOT_TOOL)
    qt_add_executable(safecloak-screenshot
        tools/screenshot_main.cpp
        src/SslIdentity.cpp
        src/FramedConnection.h
        src/FramedConnection.cpp
        src/ChatBackend.h
        src/ChatServer.h
        src/ChatServer.cpp
        src/ChatClient.h
        src/ChatClient.cpp
        src/MeshNode.h
        src/MeshNode.cpp
        src/MainWindow.h
        src/MainWindow.cpp
    )
    target_link_libraries(safecloak-screenshot PRIVATE Qt6::Widgets Qt6::Network)
endif()

option(SAFECLOAK_BUILD_TESTS "Build the headless backend smoke test" ON)
if(SAFECLOAK_BUILD_TESTS)
    qt_add_executable(safecloak-tests
        tests/test_backends.cpp
        src/SslIdentity.cpp
        src/FramedConnection.h
        src/FramedConnection.cpp
        src/ChatBackend.h
        src/ChatServer.h
        src/ChatServer.cpp
        src/ChatClient.h
        src/ChatClient.cpp
        src/MeshNode.h
        src/MeshNode.cpp
    )
    target_link_libraries(safecloak-tests PRIVATE Qt6::Core Qt6::Network)
endif()
