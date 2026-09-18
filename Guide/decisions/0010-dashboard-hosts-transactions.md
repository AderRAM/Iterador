# 0010 — Início hospeda a lista de transações; aba Transações removida

Status: Aceito

## Contexto

O usuário pediu para começar simples: uma lista de lançamentos do mês (adicionar e remover),
uma célula de total visível no canto superior direito, e um gráfico de consumo no canto
superior esquerdo — parecido com o painel "Alocações Financeiras" da planilha original (ver
[`spreadsheet-reference.md`](../spreadsheet-reference.md)). Pediu explicitamente para tirar a
aba "Transações" separada, porque a lista ficando na aba "Início" é mais prático.

Isso também exigiu implementar de verdade o CRUD de `Transaction` e `Category` — antes eram só
stubs (ver ADR-0007/0009 sobre o que já existia).

## Decisão

- `CategoryRepository` e `TransactionRepository` implementados de ponta a ponta (`listAll`,
  `findById`, `create`, e `TransactionRepository::remove` para excluir um lançamento).
- Fluxo de criação simplificado: `Application::createTransaction(description, type, amountCents,
  currency, status)` acha ou cria a categoria automaticamente a partir do texto da descrição
  (`CategoryRepository::findOrCreateByName`) — **não há tela de gerenciar categorias
  separadamente ainda**. Isso reflete como a planilha do usuário funciona hoje: não existe uma
  coluna de categoria própria, só a descrição.
- `DashboardView` (`UI/iterador_ui/views/dashboard_view.py`) virou a tela principal: botão
  "+ Adicionar" (abre `TransactionFormDialog`), um `ConsumptionChart` (gráfico de pizza
  desenhado num `tkinter.Canvas` puro, sem dependência nova, fundo sempre Carbon Black — igual
  ao gráfico da planilha) no canto superior esquerdo, e uma célula de "Total do mês" (soma de
  todos os lançamentos, colorida verde/vermelho conforme o sinal) no canto superior direito.
  Lista de lançamentos abaixo, cada um com botão "Remover".
- `TransactionsView` e a entrada "Transações" da sidebar foram **removidas**.

## Consequências

- O gráfico de consumo agrupa despesas por **descrição** (não por categoria "de verdade" nem
  pelo sistema de baldes de prioridade da planilha original) — simplificação deliberada para a
  primeira versão. Virar um gráfico por categoria/balde de orçamento fica para quando esse
  sistema for modelado (ver `spreadsheet-reference.md` > pontos em aberto).
- "Total do mês" hoje soma **todos** os lançamentos já cadastrados, sem filtrar por mês — não há
  ainda navegação entre meses nem o campo `occurred_at` exposto ao Python
  (`bind_core.cpp` não serializa `Timestamp`). Filtrar por mês de verdade é Roadmap.
- Sem tela de gerenciar categorias, o mesmo texto de descrição digitado duas vezes cria/reusa a
  mesma categoria automaticamente — categorias com nomes parecidos mas não idênticos (ex.
  "Mercado" vs "mercado") viram categorias diferentes. Aceitável para a fase atual.
