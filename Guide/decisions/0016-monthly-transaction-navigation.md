# 0016 — Navegação de transações por mês, infinita

Status: Aceito

## Contexto

O usuário mostrou um print da planilha original do Google Sheets, onde cada mês tem sua própria
aba (`02-08-26`, `05-08-26`, `06-04-26`...) e pediu o equivalente no Início: "um sistema de datas,
separado por mês onde cada mês terá as transações daquele mês, a lista de transações deve ser
capaz de expandir infinitamente [em ambas as direções], coloque um discreto contador de quantas
transações estão sendo listadas no mês selecionado".

Diferente das abas fixas da planilha, a lista de transações do Início já é única (ADR-0010) — não
dá pra simplesmente criar uma "aba" por mês sem UI nova. A navegação precisa ser ilimitada nos
dois sentidos (não um combo fixo de 12 meses), já que o usuário pode ter lançamentos de qualquer
data passada ou futura.

## Decisão

- Novo widget `UI/iterador_ui/widgets/month_selector.py` (`MonthSelector`): faixa horizontal
  rolável (`CTkScrollableFrame(orientation="horizontal")`) de botões, um por mês, com setas
  `◀`/`▶` nas pontas para deslocar o mês selecionado em ±1. Não há limite de quantos meses para
  trás/frente — `shift_month()` faz a aritmética de ano (`month=1` - 1 vira `month=12` do ano
  anterior, e vice-versa), então a navegação é matematicamente infinita nos dois sentidos.
- `update_months(available_months)` reconstrói a faixa a partir do conjunto de meses
  (`"YYYY-MM"`) que já têm alguma transação, sempre garantindo que o mês atualmente selecionado
  apareça no strip mesmo com zero transações (senão o botão selecionado sumiria da tela ao trocar
  de mês vazio).
- `DashboardView.refresh()` busca todas as transações uma vez (`backend_bridge.list_transactions()`
  já retorna tudo — sem paginação no backend ainda, volume baixo o suficiente por enquanto), extrai
  os meses distintos via `occurred_at[:7]`, atualiza o `MonthSelector`, e filtra a lista/gráfico/
  totais só pelo mês selecionado.
- Contador discreto: `"{n} lançamento(s) neste mês"` ao lado do título "Lançamentos", tamanho de
  fonte menor, sem destaque visual — só informativo.
- Cards "Receitas do período"/"Despesas do período" renomeados para "Receitas do mês"/"Despesas do
  mês", já que agora são sempre relativos ao mês selecionado, nunca ao total geral.

## Consequências

- Filtragem acontece inteiramente no lado Python, sobre a lista completa já carregada — não há
  query C++ nova por mês. Simples e correto para o volume atual; se a base crescer muito, revisitar
  para filtrar por intervalo de data direto no `TransactionRepository` (ver Roadmap).
- Editar a data de uma transação (ADR-0011) pode fazer ela "mudar de mês" e sumir da lista visível
  após salvar — comportamento esperado (a transação passou a pertencer a outro mês), mas vale
  deixar registrado caso confunda no uso real.
- O `MonthSelector` não persiste o mês selecionado entre reinícios do app — sempre abre no mês
  atual (`current_month()`). Não pedido, não implementado.
