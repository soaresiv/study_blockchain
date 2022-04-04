#Block lib
add_library(Crypto SHARED sha256.cpp sha256.h)

target_include_directories(Crypto PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

target_link_libraries(Crypto)
