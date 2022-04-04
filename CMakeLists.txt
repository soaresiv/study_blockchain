cmake_minimum_required(VERSION 3.14)

project(Blockchain LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Adding the src:
add_subdirectory(src)
