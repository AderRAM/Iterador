# 0015 — Revisão do painel "Alocações Financeiras": o que trazer, o que descartar

Status: Aceito

## Contexto

O usuário mandou o print do painel completo da planilha original (colunas G–K + gráfico) e
pediu pra eu avaliar quais variáveis valem a pena trazer pro Iterador e onde. Esse painel é o
mesmo que o usuário já tinha avisado ter um bug (ver `spreadsheet-reference.md`): os percentuais
não somam 100% e "Não Alocado" (K) aparece negativo (-26,91%), o que não faz sentido pra uma
fatia de alocação.

## Análise campo a campo

| Campo (planilha) | O que parece representar | Decisão |
|---|---|---|
| Investimento/Essencial/Desejável (%) + gráfico | Alocação por categoria | **Já trazido** — é exatamente o `ConsumptionChart` (ADR-0012/0014), calculado direto das transações reais, sem herdar o bug. |
| Output | Total de despesas do período | **Trazido** — soma simples de todas as despesas, fácil de verificar, sem ambiguidade. Card "Despesas do período". |
| Input | Total de receitas do período | **Trazido** — mesma lógica. Card "Receitas do período". |
| Capital atual / Capital final | Parecem ser saldo "antes/depois" de algo | **Reinterpretado, não copiado.** A planilha não tinha um conceito de pago/pendente por linha — o Iterador tem (`TransactionStatus`, ver ADR-0011). Em vez de tentar adivinhar a fórmula exata da planilha (arriscado dado o bug conhecido), o Iterador calcula algo parecido mas com significado claro e verificável: **"Saldo já pago"** = soma só das transações `PAID` (equivalente a "Capital atual" — o que já é seu de fato). O **"Total do mês"** que já existia (soma de tudo, pago + pendente) faz o papel de "Capital final" (projeção incluindo o que ainda vai ser pago/recebido). |
| Essencial imediato | Ambíguo — talvez despesas essenciais vencendo já | **Descartado.** Não dá pra reconstruir a fórmula com confiança a partir só do print; o "Output" já cobre o total de despesas, que é o dado sólido por trás disso. |
| Investindo (G, linha 2) | Ambíguo — talvez valor investido no período | **Descartado por agora.** Redundante com o que `Investment.current_value` já mostra na aba Investimentos; não ficou claro se seria "quanto entrou este mês" ou outra coisa. |
| Total (G, linha 3, R$ 2.432,57) | Não bate com nenhuma soma óbvia dos outros campos visíveis | **Descartado.** Não consigo verificar a fórmula, e é exatamente esse tipo de número que o usuário avisou estar errado. |
| Não Alocado (%) | Percentual negativo — sintoma do bug | **Descartado.** Uma fatia de alocação não devia ser negativa; é o próprio sintoma do bug que o usuário avisou. |

## Decisão

`DashboardView` ganhou uma fileira de 3 `StatCard` entre o Total do mês e a lista de
lançamentos: **Receitas do período**, **Despesas do período**, **Saldo já pago** — todos
calculados direto da lista de transações real (`t.amount.cents`, filtrando por sinal e por
`status`), não copiados de nenhuma fórmula da planilha. `StatCard.set_value()` ganhou um
parâmetro `color` opcional pra permitir recolorir o valor dinamicamente (usado em "Saldo já
pago", que fica verde/vermelho conforme o sinal, igual o Total do mês).

## Consequências

- "Saldo já pago" e "Total do mês" agora dão pro usuário uma leitura de "quanto eu realmente
  tenho agora" vs. "quanto eu vou ter depois que tudo que está pendente for resolvido" — uma
  distinção que a planilha original não tinha de forma confiável, e que só foi possível porque
  o Iterador já rastreia status por transação.
- Ficaram de fora do Iterador: "Essencial imediato", "Investindo" (coluna G) e "Não Alocado"
  (%) — se o usuário quiser esses conceitos de volta, precisa explicar o que cada um representa
  de verdade (a planilha com bug não é uma fonte confiável pra deduzir a fórmula).
