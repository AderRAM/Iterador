# 0013 — Desfazer/refazer e ajustes de UI no Início

Status: Aceito

## Contexto

Pacote de pedidos do usuário sobre a experiência da aba Início e da sidebar:

1. Botão de desfazer/refazer, caso ele cometa um erro ao mexer em lançamentos.
2. Botão "+ Adicionar" mais perto da lista (estava lá em cima, longe da lista).
3. Tirar o texto "Tema claro" do switch de tema — o próprio switch já é suficiente.
4. Inverter as cores do switch de tema: amarelo no estado escuro, cinza no estado claro.
5. Versão do app (`APP_VERSION`) visível em Configurações, mantida atualizada conforme marcos
   relevantes — hoje "1.0" porque o básico ainda não está pronto.

## Decisão

- `UI/iterador_ui/undo_stack.py`: `UndoStack` genérica (pilha de comandos com `.undo()`/
  `.redo()`), escopo por sessão (não persiste entre reinícios do app).
- `UI/iterador_ui/transaction_commands.py`: comandos concretos para criar/editar/remover/
  alternar status de uma transação, cada um guardando os campos necessários para reverter via
  `backend_bridge` (não mexem na UI — quem chama `refresh()` é o `DashboardView`).
  `TransactionFormDialog` agora repassa a transação criada/editada pro callback `on_created`,
  para o `DashboardView` poder registrar o comando certo.
- Botões "↶ Desfazer"/"↷ Refazer" no cabeçalho do Início. Como o ajuste de valor de investimento
  (ADR-0012) já é uma consequência de `Application::create/update/deleteTransaction`, desfazer
  uma transação ligada a um investimento também desfaz o efeito nele automaticamente — sem
  lógica extra no undo stack, testado numa sequência aporte→desfazer→refazer.
- "+ Adicionar" saiu do cabeçalho da tela e foi para uma barrinha "Lançamentos" logo acima da
  lista.
- `theme.THEME_SWITCH_DARK_COLOR` (Sunflower Gold) / `THEME_SWITCH_LIGHT_COLOR` (cinza) — trilho
  do switch (estado desligado/escuro) fica amarelo, preenchimento (estado ligado/claro) fica
  cinza. Texto do `CTkSwitch` na sidebar removido (`text=""`).
- `UI/iterador_ui/version.py` (`APP_VERSION`), exibido em `SettingsView`.

## Consequências

- Desfazer/refazer não sobrevive a fechar e reabrir o app — é só para "ops, errei agora",
  não um histórico permanente. Se precisar de histórico persistente no futuro, `operation_log`
  já guarda tudo (ver Guide/architecture.md), mas isso é um mecanismo diferente (sync, não undo
  de UI).
- Cada ação na lista limpa a pilha de "refazer" (comportamento padrão de undo/redo tipo
  editor de texto) — fazer uma ação nova depois de desfazer descarta o que dava pra refazer.
