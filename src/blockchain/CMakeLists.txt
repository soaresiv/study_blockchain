# Block lib
add_library(Block SHARED Block.cpp)

target_include_directories(Block PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

target_link_libraries(Block PUBLIC Crypto)

add_library(Blockchain SHARED Blockchain.cpp)

target_include_directories(Blockchain PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

target_link_libraries(Blockchain Block)
