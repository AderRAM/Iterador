# Iterador — contexto para assistentes de IA

Leia primeiro: [`Guide/README.md`](Guide/README.md) (índice), [`Guide/architecture.md`](Guide/architecture.md)
(como as peças se encaixam), [`Guide/file-map.md`](Guide/file-map.md) (onde fica cada coisa) e
[`Guide/dev-practices.md`](Guide/dev-practices.md) (como verificar mudanças, isolar dados de
teste, armadilhas conhecidas do CustomTkinter).

## Regras

- **Não mexer em `App/`** — é o projeto Android (Kotlin/Gradle), tratado em fase futura separada.
- **NUNCA apagar, sobrescrever ou "limpar" `~/.iterador/iterador.db`.** É o banco de dados real
  do usuário (caminho padrão hardcoded em `UI/main.py`) — não é um artefato de teste. Isso já
  aconteceu e destruiu dados reais sem backup. Qualquer teste/verificação da UI ou do backend
  deve usar um caminho de banco isolado (ex. `/tmp/iterador-*-test.db` ou algo no scratchpad),
  nunca o caminho padrão. Se precisar inspecionar o banco real, só leitura (`sqlite3 ... SELECT`),
  nunca escrita/exclusão.
- Sempre que adicionar, remover ou renomear um arquivo em `Backend/` ou `UI/`, atualize
  `Guide/file-map.md` no mesmo commit.
- Sempre que mudar a API pública exposta ao Python (métodos de `Application` em
  `Backend/src/app/`, ou funções de `UI/iterador_ui/backend_bridge.py`), atualize `Guide/functions.md`.
- Decisão arquitetural nova → novo ADR em `Guide/decisions/`. Nunca editar um ADR antigo; marque
  como "Superseded by ADR-000X" se for substituído.
- Código modular: um arquivo por responsabilidade, evite concentrar lógica em scripts grandes.
- **Mudança de schema do banco**: nunca editar `Backend/src/storage/migrations/0001_init.sql`
  (ou qualquer migration já embutida em release) — o usuário já tem dados reais migrados. Criar
  a próxima `000N_*.sql`, adicionar `@MIGRATION_000N_SQL@` em `EmbeddedMigrations.hpp.in`, ler o
  arquivo em `CMakeLists.txt`, e um bloco novo `if (currentUserVersion() < N)` em
  `Database::runMigrations()`. Testar sempre simulando um banco na versão anterior antes de
  considerar pronto (ver como foi feito na migration 0002).
- `UI/iterador_ui/version.py` guarda a versão do app (`APP_VERSION`), mostrada em
  Configurações. Está em "1.0" porque o básico (CRUD completo, sync) ainda não está pronto —
  atualizar esse número conforme marcos relevantes forem concluídos, não a cada mudança pequena.

## Comandos essenciais

```bash
./scripts/setup_dev_env.sh   # cria venv, instala dependências Python
./scripts/build_backend.sh   # compila Backend/ com CMake, gera UI/_build/iterador_core*.so
./scripts/run_ui.sh          # roda a UI CustomTkinter
ctest --test-dir Backend/build   # testes C++
```

Pré-requisito desta máquina de desenvolvimento: `cmake` precisa estar instalado (não vem por padrão).
