# Resolve as dependências externas do Backend. Mantido separado do CMakeLists.txt raiz para
# esse ficar curto e legível (ver Guide/architecture.md).

include(FetchContent)

# pybind11 — tenta achar a instalação via pip primeiro (mais rápido, sem clone git), com
# fallback para FetchContent se não estiver instalado no ambiente.
find_package(pybind11 CONFIG QUIET)
if(NOT pybind11_FOUND)
  FetchContent_Declare(pybind11
    GIT_REPOSITORY https://github.com/pybind/pybind11.git
    GIT_TAG v2.13.6)
  FetchContent_MakeAvailable(pybind11)
endif()

# SQLite via amalgamation: evita depender de libsqlite3-dev (Linux) ou de algo equivalente no
# Windows, e evita commitar o sqlite3.c gigante no repositório (ADR-0004).
# Sem URL_HASH de propósito: a versão exata do arquivo muda conforme o release do SQLite e
# fixar um hash errado quebraria o download. Se quiser checagem de integridade, adicione
# URL_HASH SHA256=<hash real do arquivo> depois de baixar e conferir em sqlite.org/download.html.
FetchContent_Declare(sqlite3_amalgamation
  URL https://www.sqlite.org/2024/sqlite-amalgamation-3450000.zip)
FetchContent_MakeAvailable(sqlite3_amalgamation)

add_library(sqlite3 STATIC ${sqlite3_amalgamation_SOURCE_DIR}/sqlite3.c)
# `iterador_core` é um módulo compartilhado (.so, ver pybind11_add_module) — objeto estático
# linkado nele precisa ser PIC, senão o link final falha ("recompile com -fPIC"). Bug de
# configuração pré-existente, mesmo motivo do `project(... LANGUAGES CXX C)` acima: nenhum
# rebuild limpo tinha sido feito nesta máquina até agora pra expor isso.
set_target_properties(sqlite3 PROPERTIES POSITION_INDEPENDENT_CODE ON)
target_include_directories(sqlite3 PUBLIC ${sqlite3_amalgamation_SOURCE_DIR})
if(UNIX)
  target_link_libraries(sqlite3 PUBLIC pthread ${CMAKE_DL_LIBS})
endif()
