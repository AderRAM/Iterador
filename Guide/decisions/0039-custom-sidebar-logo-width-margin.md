# 0039 — Margem lateral reduzida: imagem mais larga

Status: Superseded by [ADR-0040](0040-sidebar-fixed-width-and-final-logo-size.md) — a
Sidebar não travava a própria largura (`pack_propagate` nunca desligado), então ela crescia
sozinha pra caber qualquer imagem — toda medição de "quanto espaço sobra" feita nesta ADR (e na
anterior) estava medindo uma borda que tinha se movido junto, não uma margem real. O raciocínio
de "calcular o máximo, não chutar" continua certo — só a Sidebar não tinha, de fato, um máximo
antes da ADR-0040.

Supersede [ADR-0038](0038-custom-sidebar-logo-size.md).

## Contexto

ADR-0038 fixou `LOGO_SIZE = (162, 130)` usando `padx=8` (mesma margem dos itens de navegação da
Sidebar) como "respiro seguro". Usuário testou, comparou visualmente a altura (bem maior, correto
— ~3x a do `TriangleHeading`) com a largura (quase igual, 162 vs 156px, imperceptível) e marcou
com uma anotação visual quanto espaço sobrava sem usar entre a imagem e a borda real da Sidebar
— nitidamente mais do que os 8px usados.

## Decisão: margem mínima real, não emprestar a margem de outro elemento

`padx=8` era emprestado dos itens de navegação sem necessidade — não existe nenhum motivo pra
imagem customizada usar a MESMA margem que botões de navegação, ela só precisa da margem mínima
pra literalmente não encostar na borda de 1px da Sidebar. Reduzido pra `padx=3` — Sidebar
interior é 178px (180 - 2×1 de borda), `178 - 2×3 = 172px` de largura máxima, contra os 162px
anteriores.

`sidebar.py` e `sidebar_image.py` (`LOGO_SIZE`) atualizados juntos — o `padx` do
`.pack()` em `sidebar.py` e a largura calculada em `LOGO_SIZE` precisam continuar consistentes
entre si (um é o resultado do outro), documentado nos dois lugares.

## Consequências

- Mesma ressalva de ADR-0038: imagens já salvas com o tamanho anterior (162×130) precisam ser
  reenviadas pra aproveitar a largura nova — sem upscale automático.
- Testado (Xvfb, `$HOME` isolado): imagem nova sai 172×130, `Iterador` continua visível embaixo,
  sem encostar na borda da Sidebar.
