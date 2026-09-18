include(FetchContent)
FetchContent_Declare(doctest
  GIT_REPOSITORY https://github.com/doctest/doctest.git
  GIT_TAG v2.4.11)
FetchContent_MakeAvailable(doctest)

add_executable(iterador_tests
  test_money.cpp
  ${CMAKE_SOURCE_DIR}/src/core/Money.cpp)

target_include_directories(iterador_tests PRIVATE ${CMAKE_SOURCE_DIR}/src)
target_link_libraries(iterador_tests PRIVATE doctest::doctest)

include(${doctest_SOURCE_DIR}/scripts/cmake/doctest.cmake)
doctest_discover_tests(iterador_tests)
