# 0022 — Investimento vinculado a lançamento virou opcional (genérico)

Status: Aceito

## Contexto

Ao desenhar o importador da planilha Excel do usuário (ver ADR-0023), ~38 lançamentos históricos
de categoria "Investimento"/"Passiva" não têm como saber a qual `Investment` específico do
Iterador cada um deveria se ligar — a planilha só tem uma descrição livre ("investimentos",
"investimento Notebook", "Saque investimento"...), não um identificador de investimento.

Vincular todos arbitrariamente a um único `Investment` (ex. "Caixinha Nubank") distorceria o
valor dele com ~100+ ajustes retroativos de uma vez (a lógica de `adjustInvestmentValue`, ver
ADR-0012, foi pensada pra lançamento do dia a dia, não pra reconstruir histórico). O usuário
pediu, em vez disso, que ficar sem investimento vinculado numa categoria Investimento/Passiva
vire uma opção de verdade — um "investimento genérico" sem rótulo, rotulável depois.

## Decisão

- Nenhuma mudança em C++: `Application::adjustInvestmentValue` (`Application.cpp:39-52`) **já**
  trata `investmentId` vazio como "não faz nada" (`if (investmentId.empty() || deltaCents == 0)
  return;`) — o backend já suportava isso desde o ADR-0012, só a UI não deixava escolher.
- `TransactionFormDialog` (`UI/iterador_ui/widgets/transaction_form_dialog.py`) ganhou uma opção
  fixa `"Nenhum (genérico)"` no seletor de investimento, sempre presente e selecionada por
  padrão — inclusive quando não há nenhum `Investment` cadastrado (antes isso bloqueava o
  formulário com "Cadastre um investimento antes de ligar um lançamento a ele.").
- "Rotular depois" não precisou de nenhuma tela nova: editar o lançamento e trocar o seletor de
  "Nenhum (genérico)" pra um investimento real já funciona, porque `update_transaction` já
  reverte o efeito no investimento antigo (vazio = nenhum efeito) e aplica no novo — mesmo
  caminho de código de sempre (ADR-0012).
- Importador de planilha (ADR-0023) usa isso: todo lançamento de categoria Investimento/Passiva
  vindo do Excel entra com `investment_id=""`.

## Consequências

- Lançamentos "genéricos" de Investimento/Passiva aparecem na lista/gráfico de consumo
  normalmente (contam pra categoria), só não afetam nenhum `Investment.current_value`.
- Não há, ainda, nenhum resumo/total agregado dos lançamentos "genéricos" (ex. "R$ X em
  investimentos sem rótulo") — só aparecem individualmente na lista de lançamentos. Se isso for
  pedido, é um card novo somando `Transaction` com categoria Investimento/Passiva e
  `investment_id == ""`, sem precisar de mudança de schema.
