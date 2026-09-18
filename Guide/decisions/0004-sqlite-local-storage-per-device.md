# 0004 — SQLite como armazenamento local por dispositivo

Status: Aceito

## Contexto

Com o modelo P2P (ADR-0003), cada dispositivo precisa de um banco de dados local, embutido, sem
processo servidor de banco separado, disponível em Linux, Windows e (futuramente) Android.

## Decisão

Usar **SQLite** via amalgamation (`sqlite3.c`/`sqlite3.h` baixados por `FetchContent` no CMake),
compilado como parte do `Backend/`. Todas as mutações também gravam uma entrada em
`operation_log`, que é a base do sync (event sourcing) — ver `Backend/src/storage/OperationLog.*`.

## Consequências

- Sem dependência de sistema (`libsqlite3-dev` etc.) — o `sqlite3.c` é baixado e compilado junto,
  o que simplifica build cross-platform (Linux/Windows) e facilita portar para Android depois.
- `operation_log` cresce indefinidamente enquanto não houver compactação/poda — isso é aceitável
  na fase atual e fica registrado no roadmap (`Guide/architecture.md`) como algo a revisar.
- Todo acesso ao banco passa por `Database` (RAII, mutex interno), nunca SQL solto espalhado pelo
  código — repositórios são a única camada que escreve SQL.
