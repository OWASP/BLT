cmake_minimum_required(VERSION 3.16)
project(SafeCloak VERSION 0.7.0 LANGUAGES CXX)

# Baked into the binaries: shown in the UI, and the quick-update button uses
# the source dir to git pull + rebuild when running from a checkout.
add_compile_definitions(
    SAFECLOAK_VERSION="${PROJECT_VERSION}"
    SAFECLOAK_SOURCE_DIR="${CMAKE_CURRENT_SOURCE_DIR}"
)

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
    src/MeshNode.h
    src/MeshNode.cpp
    src/MessageRow.h
    src/MessageRow.cpp
    src/SettingsDialog.h
    src/SettingsDialog.cpp
    src/MainWindow.h
    src/MainWindow.cpp
)

target_link_libraries(safecloak PRIVATE Qt6::Widgets Qt6::Network)

option(SAFECLOAK_BUILD_TESTS "Build the headless backend smoke test" ON)
if(SAFECLOAK_BUILD_TESTS)
    qt_add_executable(safecloak-tests
        tests/test_backends.cpp
        src/SslIdentity.cpp
        src/FramedConnection.h
        src/FramedConnection.cpp
        src/ChatBackend.h
        src/MeshNode.h
        src/MeshNode.cpp
    )
    target_link_libraries(safecloak-tests PRIVATE Qt6::Core Qt6::Network)
endif()
