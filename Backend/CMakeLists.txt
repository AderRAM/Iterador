cmake_minimum_required(VERSION 3.18)
# C além de CXX: o alvo `sqlite3` (Dependencies.cmake) compila sqlite3.c puro (amalgamation, ver
# ADR-0004) — sem C habilitado aqui, CMake não consegue decidir o linker desse alvo ("cannot
# determine linker language"). Bug de configuração pré-existente, nunca disparado antes porque
# nenhum rebuild limpo tinha sido feito nesta máquina até agora.
project(iterador_core LANGUAGES CXX C)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

option(ITERADOR_BUILD_TESTS "Build unit tests" ON)

include(cmake/Dependencies.cmake)

# Embute src/storage/migrations/*.sql no binário (ver
# src/storage/migrations/EmbeddedMigrations.hpp.in) — o .sql é a fonte da verdade legível,
# o header gerado só existe para não escrever SQL como string C++ escapada à mão.
# Nova migration: ler o arquivo aqui + adicionar @MIGRATION_000N_SQL@ no .hpp.in + um bloco
# novo em Database::runMigrations() — nunca editar uma migration já embutida em release.
file(READ ${CMAKE_CURRENT_SOURCE_DIR}/src/storage/migrations/0001_init.sql MIGRATION_0001_SQL)
file(READ ${CMAKE_CURRENT_SOURCE_DIR}/src/storage/migrations/0002_link_transaction_investment.sql MIGRATION_0002_SQL)
file(READ ${CMAKE_CURRENT_SOURCE_DIR}/src/storage/migrations/0003_redesign_budgets_as_goals.sql MIGRATION_0003_SQL)
file(READ ${CMAKE_CURRENT_SOURCE_DIR}/src/storage/migrations/0004_add_transaction_sort_order.sql MIGRATION_0004_SQL)
file(READ ${CMAKE_CURRENT_SOURCE_DIR}/src/storage/migrations/0005_add_transaction_recurring_flag.sql MIGRATION_0005_SQL)
configure_file(
  src/storage/migrations/EmbeddedMigrations.hpp.in
  ${CMAKE_CURRENT_BINARY_DIR}/generated/EmbeddedMigrations.hpp
  @ONLY)

set(CORE_SOURCES
  src/core/Money.cpp
  src/core/Category.cpp
  src/core/Transaction.cpp)

set(STORAGE_SOURCES
  src/storage/Database.cpp
  src/storage/InvestmentRepository.cpp
  src/storage/CategoryRepository.cpp
  src/storage/TransactionRepository.cpp
  src/storage/BudgetRepository.cpp
  src/storage/OperationLog.cpp)

set(SYNC_SOURCES
  src/sync/net/PlatformSocket.cpp
  src/sync/PeerDiscovery.cpp
  src/sync/TailscalePeerSource.cpp
  src/sync/SyncProtocol.cpp
  src/sync/HybridLogicalClock.cpp
  src/sync/SyncEngine.cpp)

set(APP_SOURCES
  src/app/Application.cpp)

set(BINDINGS_SOURCES
  src/bindings/module.cpp
  src/bindings/bind_core.cpp
  src/bindings/bind_app.cpp)

pybind11_add_module(iterador_core
  ${BINDINGS_SOURCES}
  ${CORE_SOURCES}
  ${STORAGE_SOURCES}
  ${SYNC_SOURCES}
  ${APP_SOURCES})

target_include_directories(iterador_core PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_BINARY_DIR})

target_link_libraries(iterador_core PRIVATE sqlite3)

if(WIN32)
  target_link_libraries(iterador_core PRIVATE ws2_32)
endif()

if(MINGW)
  # Sem isso, o .pyd final depende de libgcc_s_seh-1.dll/libstdc++-6.dll/libwinpthread-1.dll do
  # runtime do mingw-w64 — DLLs que não vêm com o Windows nem com o Python empacotado pelo
  # instalador (ver Guide/decisions/0035-packaging-and-installers.md). Estático aqui faz o .pyd
  # não depender de mais nada do compilador, só de python3XX.dll e de DLLs do próprio Windows.
  target_link_options(iterador_core PRIVATE -static-libgcc -static-libstdc++ -static -lwinpthread)
endif()

# Copia o binário compilado direto para UI/_build — assim
# UI/iterador_ui/backend_bridge.py só precisa apontar para um caminho fixo (ver Guide/usage.md).
set_target_properties(iterador_core PROPERTIES
  LIBRARY_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/../UI/_build
  RUNTIME_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/../UI/_build)

if(ITERADOR_BUILD_TESTS)
  enable_testing()
  add_subdirectory(tests)
endif()
