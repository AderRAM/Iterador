# 0018 — Navegação por mês limitada aos meses existentes + botão "+ Mês"

Status: Aceito

## Contexto

O ADR-0016 implementou navegação por mês nas setas ◀/▶ como um deslocamento aritmético (`shift_month`,
±1 mês) sem limite nenhum — dava pra ficar avançando pra sempre em meses futuros vazios, sem
nenhum sinal de que aquele mês "não existe de verdade" ainda. O usuário relatou que isso parecia
"bugado" e pediu duas coisas: (1) as setas não deveriam deixar avançar quando não há mês pra
avançar; (2) um jeito explícito de adicionar um mês novo (botão + caixa de texto), já que a única
forma de criar um mês "do nada" seria abrir o diálogo de novo lançamento e digitar uma data nele.

## Decisão

- `MonthSelector` agora guarda os meses conhecidos como uma lista ordenada
  (`self._months_sorted` = meses com lançamento ∪ meses adicionados manualmente ∪ mês
  selecionado). `_go_previous`/`_go_next` navegam por **índice** nessa lista, não mais por
  aritmética de calendário — se não há próximo/anterior na lista, não faz nada.
- Os botões ◀/▶ ficam com `state="disabled"` (visualmente acinzentados, CustomTkinter cuida do
  estilo) quando o mês selecionado é o primeiro/último da lista — reforça visualmente o limite,
  não é só o clique que vira no-op.
- Removida a função `shift_month()` (não tem mais nenhum uso — a navegação não é mais aritmética).
- Novo botão "+ Mês" ao lado da seta ▶, abre `AddMonthDialog`
  (`UI/iterador_ui/widgets/add_month_dialog.py`) — um campo de texto "MM/AAAA" (aceita também
  "AAAA-MM"), valida com `datetime.strptime`, e adiciona o mês à tira já selecionado.
- Meses adicionados manualmente (`self._extra_months`) ficam guardados só na instância do
  widget — não persistem no banco nem sobrevivem trocar de aba e voltar pro Início (que já
  recria toda a `DashboardView`, incluindo o mês selecionado reiniciando pro mês atual — esse
  reset não é novo desta mudança, já existia desde o ADR-0016). Não pedido, não implementado:
  se isso incomodar no uso real, o próximo passo natural é persistir "meses adicionados" em
  algum lugar (ex. tabela nova ou até inferir a partir de uma transação futura já cadastrada).
- Um mês adicionado manualmente sem nenhum lançamento continua aparecendo na tira normalmente
  (mesma lógica de "mês selecionado sempre aparece" do ADR-0016) até que a `DashboardView` seja
  recriada.

## Consequências

- Criar uma transação com uma data de um mês que ainda não está na tira (via edição manual da
  data no formulário, sem passar pelo "+ Mês") também faz esse mês aparecer — `update_months()`
  usa a união de todas as fontes, então não há regressão aí.
- Sem persistência do "mês adicionado" entre reaberturas do app, então adicionar um mês futuro
  só pra "reservar o espaço" sem lançar nada nele se perde ao fechar o app ou trocar de aba —
  aceitável para o caso de uso principal (adicionar o mês pra já lançar algo nele em seguida).
