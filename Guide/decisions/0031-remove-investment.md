# 0031 — Remover investimento

Status: Aceito

## Contexto

Não existia nenhuma forma de apagar um investimento — nem no banco (`InvestmentRepository` só
tinha `create`/`update`/`listAll`/`findById`), nem exposto a Python (`Application`/bindings). O
usuário pediu essa opção. Diferente das remoções mais recentes desta sessão (categoria
personalizada, perfil de cor — só JSON local), isso precisa mexer no SQLite via C++, então
precisou recompilar o Backend.

## Dois bugs de build pré-existentes, descobertos no processo

Esta era a primeira vez nesta sessão (e aparentemente a primeira vez em muito tempo) que o
Backend foi recompilado do zero nesta máquina depois que `cmake` foi instalado. Isso expôs 2
problemas de configuração que nunca tinham sido testados:

1. `Backend/CMakeLists.txt` declarava `project(iterador_core LANGUAGES CXX)` — só C++. O alvo
   `sqlite3` (`Dependencies.cmake`) compila `sqlite3.c` puro (amalgamation, ver ADR-0004), e sem
   `C` habilitado no `project()`, o CMake não consegue decidir o linker desse alvo ("cannot
   determine linker language"). Corrigido: `project(iterador_core LANGUAGES CXX C)`.
2. O alvo `sqlite3` (biblioteca estática) não tinha `POSITION_INDEPENDENT_CODE` — linkar um
   objeto não-PIC dentro de `iterador_core.so` (um módulo compartilhado) falha no linker final
   ("recompile com -fPIC"). Corrigido: `set_target_properties(sqlite3 PROPERTIES
   POSITION_INDEPENDENT_CODE ON)`.

Também: `ITERADOR_BUILD_TESTS` (que baixa `doctest` via git) foi desligado nesta build
(`-DITERADOR_BUILD_TESTS=OFF`) porque o clone deu erro de "dubious ownership" do git no diretório
de build recém-criado (o repo inteiro está num disco montado externo). Não editei configuração
global de git pra contornar isso (regra do `CLAUDE.md`) — só desliguei os testes C++ pra esta
build. Sem perda real: `Backend/tests/` só tinha `test_money.cpp`, nada relacionado a
`InvestmentRepository`. Verificação ficou por conta de testes de integração em Python contra
cópias do banco real (ver Verificação abaixo).

## Decisão

- **`InvestmentRepository::remove(id)`** (novo) — `DELETE FROM investments WHERE id = ?`, mesmo
  padrão de `TransactionRepository::remove`/`BudgetRepository::remove` (erro se `id` não existe,
  entrada em `OperationLog`).
- **`TransactionRepository::clearInvestmentLink(investmentId)`** e
  **`BudgetRepository::clearInvestmentLink(investmentId)`** (novos) — `UPDATE ... SET
  investment_id = NULL WHERE investment_id = ?`. A FK `investment_id REFERENCES investments(id)`
  tem `foreign_keys=ON` (`Database.cpp`) — apagar um investimento ainda referenciado falharia
  direto; em vez de bloquear a remoção ou (pior) apagar em cascata os lançamentos/metas, essas
  linhas só perdem o vínculo (`investment_id` vira `""`/NULL, o mesmo estado de "Nenhum
  (genérico)" já existente desde ADR-0022) — nenhum lançamento ou meta de economia é apagado por
  causa da remoção de um investimento, mesmo princípio de nunca destruir dado histórico usado em
  toda a sessão (categoria órfã "Necessário", categoria personalizada removida, etc.).
- **`Application::deleteInvestment(id)`** (novo) — chama os dois `clearInvestmentLink` antes de
  `investments_.remove(id)`.
- **`bind_app.cpp`**: `delete_investment(id)`. **`backend_bridge.py`**: `delete_investment(investment_id)`, repassa.
- **`investments_view.py`**: botão "Remover" em cada linha (ao lado de "Editar"), mesmo padrão de
  `ConfirmDialog` já usado em outras remoções desta sessão.

## Verificação

Contra banco de scratch (nunca `~/.iterador/iterador.db`): criar investimento, criar transação E
orçamento vinculados a ele, remover o investimento, confirmar — investimento sumiu de
`list_investments()`; a transação e o orçamento continuam em `list_transactions()`/
`list_budgets()`, ambos com `investment_id == ""`; remover um id inexistente lança erro. Testado
também pela árvore de widgets de verdade (`InvestmentsView`): botão "Remover" existe, abre
`ConfirmDialog`, clicar "Remover" no diálogo remove de verdade e atualiza a lista. Smoke test
completo (5 abas) depois, com o binário recompilado.
