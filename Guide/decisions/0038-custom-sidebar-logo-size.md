# 0038 — Tamanho máximo seguro da imagem customizada da Sidebar

Status: Superseded by [ADR-0039](0039-custom-sidebar-logo-width-margin.md) — a margem de
segurança usada aqui (`padx=8`, igual aos itens de navegação) era maior que o necessário; o
usuário mostrou visualmente que sobrava espaço não aproveitado. O resto deste documento (por que
calcular o máximo em vez de chutar, por que a altura não tem teto rígido) continua válido — só o
número final de largura mudou.

## Contexto

ADR-0036 fixou a imagem customizada em 156×90px (mesma largura do `TriangleHeading` original).
Usuário pediu de novo, depois de ver o resultado: precisa ser maior que o retângulo "Iterador",
sem encostar na borda da Sidebar, "de forma que provida a melhor resolução" — ou seja, não só
"maior que antes", mas o **maior possível** dentro do espaço disponível, pra imagem enviada
perder o mínimo de detalhe/nitidez ao ser redimensionada.

## Decisão: calcular o máximo real, não chutar um número maior

`Sidebar` (`UI/iterador_ui/widgets/sidebar.py`) tem `width=180` com `border_width=1` de cada
lado (interior = 178px). Os próprios itens de navegação da Sidebar já usam `padx=8` sem
encostar na borda (`sidebar.py`, loop de `_NAV_ITEMS`) — reaproveitando essa mesma margem já
comprovada seguro pra imagem customizada: `178 - 2×8 = 162px` de largura máxima. Essa é a
largura nova de `sidebar_image.LOGO_SIZE` (era 156). Altura foi de 90 pra 130px — sem teto
rígido (a Sidebar cresce em altura livremente, `pack(fill="y")` em `app.py`), aumentada bem além
do necessário só pra "ser maior" — dá mais espaço de verdade pra imagem manter resolução.

`LOGO_SIZE` virou constante pública em `sidebar_image.py` (era `_TARGET_SIZE`, privada) —
`sidebar.py` agora lê de lá em vez de repetir os números na hora de montar o `CTkImage`,
evitando os dois arquivos saírem de sincronia se o tamanho mudar de novo.

## Consequências

- Imagens enviadas antes desta mudança (salvas em 156×90) precisam ser reenviadas pelo usuário
  pra aproveitar o tamanho novo — `set_custom_logo()` sempre reprocessa do zero a partir do
  arquivo original escolhido no diálogo, não existe "upscale" automático de um logo já salvo.
- Testado (Xvfb, `$HOME` isolado): imagem nova sai 162×130, continua sem encostar na borda da
  Sidebar, "Iterador" continua visível embaixo (ADR-0037 intacto).
