# 0042 — Contorno preto no texto da coluna Categoria

Status: Aceito

## Contexto

Usuário relatou baixa visibilidade do texto da coluna "Categoria" (lista de lançamentos, Início)
no modo claro — a cor vem de `theme.category_label_color()`/`category_color()` (cor fixa por
categoria ou, pra personalizada, a cor escolhida pelo usuário/hash determinístico, ver
ADR-0028/0030), usada direto como `text_color` do texto. Tons pastel/claros (comuns em paletas
de categoria personalizada, e no próprio perfil "Roze Quartz", ver ADR-0041) ficam com contraste
ruim contra fundos claros — o mesmo problema que `TriangleHeading` já resolveu pro título
"Iterador" com um contorno branco por letra.

## Decisão: `OutlinedLabel`, um `tk.Canvas` reutilizável

`CTkLabel`/Tkinter não tem contorno de texto nativo — a única forma de simular isso é a mesma
técnica de `TriangleHeading._draw_outlined_text()`: desenhar o texto 8 vezes em preto, 1px de
offset em cada direção, com a cor real por cima. Novo widget
`UI/iterador_ui/widgets/outlined_label.py` generaliza essa técnica pra texto de largura
variável (nome de categoria muda) em vez do retângulo fixo do logo — mede o texto
(`tkfont.Font.measure`) e redimensiona o próprio Canvas a cada `set_text()`.

Só a coluna "Categoria" da lista do Início foi trocada
(`views/dashboard_view.py`, era `ctk.CTkLabel(..., text_color=theme.category_label_color(...))`)
— as legendas do gráfico de pizza e do comparativo mensal (`consumption_chart.py`/
`line_chart.py`) **já** usam `theme.TEXT_PRIMARY` pro nome da categoria (a cor da categoria só
aparece na bolinha/linha ao lado, não no texto) — não tinham esse problema, não precisaram mudar.

## Decisão: fundo sólido, não "transparente"

`tk.Canvas` não tem fundo "transparent" de verdade (diferente de `CTkLabel`, que deixa mostrar o
que está atrás) — `OutlinedLabel` resolve `theme.BG_APP` (par claro/escuro) pra uma cor sólida
via `ctk.get_appearance_mode()` a cada `set_text()`. Isso quebrava o "elevar" visual da linha
durante o arrasto (ver ADR-0033: `CTkLabel` da linha arrastada ganha `fg_color=BG_SURFACE`
temporário, cobrindo por cima do fundo sólido do cartão de arrasto) — resolvido com
`set_background()`/`reset_background()` dedicados, chamados nos mesmos pontos de
`_on_handle_press`/`_on_handle_release` que já tratavam isso pra `CTkLabel`.

## Bug real encontrado e corrigido: `tk.Canvas` sobrescreve `.lift()`/`.tkraise()`

`Canvas` (tkinter) redefine `lift`/`tkraise` como alias de `tag_raise` (levantar um ITEM do
canvas, não a janela do widget) — `DashboardView._show_card_bg` chama `widget.lift()`
genericamente em todo widget da linha durante o arrasto, o que quebrava (`TclError: wrong #
args`) assim que a linha continha um `OutlinedLabel`. Corrigido em dois lugares: o site de
chamada trocou pra `.tkraise()` (mais correto semanticamente, ainda quebraria sozinho); e
`OutlinedLabel` sobrescreve `tkraise`/`lift` de volta pro comportamento normal de janela
(`self.tk.call("raise", self._w, aboveThis)`, mesma implementação de `tkinter.Misc.tkraise`) —
sem isso, arrastar qualquer lançamento derrubava a UI com uma exceção não tratada.

## Consequências

- Testado (Xvfb, perfil "Roze Quartz" + modo claro — cenário real que motivou o relato): texto
  de categoria com contorno preto nítido contra fundo pastel, legível. Arrastar um lançamento
  (mesmo fluxo do ADR-0033) testado de novo depois da mudança — sem exceção, sem quebrar o
  "elevar" visual da linha.
- `OutlinedLabel` guarda `(texto, cor)` já desenhados e pula redesenho se nada mudou (mesmo
  princípio de "diff antes de redesenhar" já usado em `ConsumptionChart`/`LineChart` pro
  "piscar", ver checklist) — evita custo de redesenho em toda renderização da lista quando a
  categoria da linha não mudou.
