# 0040 — Sidebar com largura travada + tamanho final da imagem

Status: Aceito

Supersede [ADR-0039](0039-custom-sidebar-logo-width-margin.md).

## Contexto

Usuário testou a largura maior (ADR-0039, 172px) e pediu pra dobrar o aumento. Antes de simplesmente
aumentar o número de novo, medi os pixels reais do print que ele mandou (com uma anotação
mostrando espaço não usado) — e o espaço realmente parecia sobrar bem mais do que o esperado.
Investigando por que: `Sidebar` (`UI/iterador_ui/widgets/sidebar.py`) é um `ctk.CTkFrame` criado
com `width=180`, mas **nunca chamava `pack_propagate(False)`** — em Tkinter, sem isso, um frame
com filhos (`pack(fill="x")`) que sejam mais largos que o `width` declarado faz o **frame inteiro
crescer** pra caber o filho. Ou seja: toda vez que a `LOGO_SIZE` era aumentada, a Sidebar toda
ficava mais larga pra acomodar — a "borda" que eu estava medindo tinha se movido junto com a
imagem, então nunca vi ela "encostar" de verdade, não importa o quão grande o número fosse
(testado até 300px: a Sidebar simplesmente virava mais larga que 180px sozinha).

## Decisão: travar a largura da Sidebar, aí sim calcular o máximo real

`self.pack_propagate(False)` adicionado logo após o `super().__init__()` de `Sidebar` — agora
`width=180` é um limite de verdade, não um tamanho inicial. Confirmado empiricamente: pedindo
uma imagem de 300px de largura, ela agora **é cortada** pela Sidebar (que continua com 180px) —
prova de que o travamento funciona. Com isso, o cálculo original (interior = 180 - 2×1 de borda
= 178px) finalmente corresponde à realidade.

**Tamanho final**: `LOGO_SIZE = (174, 130)`, `padx=2` em `sidebar.py` — `178 - 2×2 = 174px`,
sobrando só ~1-2px de respiro real até a borda da Sidebar (medido por pixel no screenshot de
teste). Não dá pra ir além disso sem ou encostar na borda, ou alargar a própria Sidebar (mudança
de layout maior, fora de escopo aqui — o usuário não pediu isso).

## Consequências

- Esse era um bug real e pré-existente na Sidebar (não é específico da imagem customizada) —
  antes desta ADR, QUALQUER filho da Sidebar mais largo que 180px silenciosamente alargava a
  barra inteira em vez de ser cortado ou dar erro. Só nunca tinha sido notado porque nenhum
  filho, até a imagem customizada, era largo o bastante pra disparar isso.
- Mesma ressalva das ADRs anteriores: imagem já salva num tamanho antigo precisa ser reenviada
  pra aproveitar o tamanho novo.
- Testado (Xvfb, `$HOME` isolado): 174×130 renderiza com margem mínima real e sem cortar; 300px
  de teste confirma que agora CORTA em vez de alargar a Sidebar — ambos os comportamentos
  esperados confirmados visualmente, não só calculados.
