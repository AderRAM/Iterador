# 0037 — Imagem customizada aparece ACIMA do "Iterador", não no lugar dele

Status: Aceito

Supersede [ADR-0036](0036-custom-sidebar-logo-image.md).

## Contexto

ADR-0036 implementou a imagem customizada da Sidebar substituindo `TriangleHeading` (mosaico +
texto "Iterador") quando configurada. Depois de testar de verdade, o usuário relatou: "o
iterador desapareceu, essa parte não deveria acontecer" — a marca "Iterador" precisa continuar
visível sempre, mesmo com uma imagem customizada ativa. Em retrospecto, o pedido original
("carregar uma imagem pra aparecer em cima de Iterador") já dizia isso de forma literal — "em
cima de", não "no lugar de" — mal interpretado na ADR-0036.

## Decisão: empilhar, não substituir

`Sidebar.__init__` (`UI/iterador_ui/widgets/sidebar.py`) volta a construir `TriangleHeading`
**sempre**, incondicionalmente — igual antes de ADR-0036 existir. Quando existe uma imagem
customizada (`sidebar_image.get_logo_path()`), ela é empacotada **acima** do `TriangleHeading`
(mesma largura/padding, `pady=(16, 8)`), e o próprio `TriangleHeading` perde só o `pady` de cima
(`0` em vez de `16`, já que agora não é mais o primeiro elemento) — sem imagem customizada, tudo
continua pixel-idêntico ao comportamento original.

Nenhuma mudança em `sidebar_image.py` (processamento/persistência da imagem, 156×90px + borda
preta de 4px) nem no card "Imagem da barra lateral" de `settings_view.py` — só a composição
visual em `sidebar.py` mudou.

## Consequências

- Sidebar fica mais alta quando há imagem customizada (~90px a mais antes dos itens de
  navegação) — aceito, sem problema de espaço numa janela de 900px de altura mínima.
- Testado de novo (Xvfb, `$HOME` isolado): com imagem customizada ativa, "Iterador" continua
  visível abaixo dela; sem imagem, layout idêntico ao de antes da ADR-0036.
