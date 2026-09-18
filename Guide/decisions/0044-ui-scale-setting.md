# 0044 — Escala geral da interface (90%–150%)

Status: Aceito

## Contexto

Usuário pediu duas coisas juntas: uma opção pra mudar "o tamanho das letras" e outra pra "a
interface... maior e com mais visibilidade", citando Blender/AutoCAD/navegadores como
referência. Esses três exemplos, sem exceção, implementam isso como **um fator de escala só**
(não um controle separado só pra fonte e outro só pros widgets) — CustomTkinter já tem exatamente
esse primitivo pronto (`ctk.set_widget_scaling()`, escala largura/altura/fonte de todo widget
junto), então as duas partes do pedido viram a mesma configuração.

## Decisão: `ctk.set_widget_scaling()`, sem `rebuild_ui()` (na maior parte)

Diferente de trocar de perfil de cor (ADR-0025) ou imagem da sidebar (ADR-0037), CustomTkinter
**já reescala todo widget construído sozinho** — `ScalingTracker.set_widget_scaling()` chama um
callback registrado em cada widget existente (confirmado lendo o código fonte da lib, não só
supondo). Não precisava de `on_visuals_changed`/reconstruir nada pra maioria da UI.

Opções fixas (`theme.UI_SCALE_OPTIONS = (0.9, 1.0, 1.1, 1.25, 1.5)`, mesmo espírito de
`APPEARANCE_MODES`) em vez de um slider contínuo — mais simples de validar/persistir, e
`CTkSegmentedButton` já é o padrão usado em outros lugares da tela de Configurações.

## Decisão: `preferences.py` virou round-trip genérico

Só tinha `appearance_mode`, sobrescrevendo o arquivo inteiro a cada save — funcionava porque só
existia um campo. Adicionar `ui_scale` exigia parar de sobrescrever: `_load()`/`_save()` agora
fazem round-trip completo (lê tudo, guarda tudo), mesmo padrão que `color_profiles.py`/
`custom_categories.py` já usavam — sem isso, salvar a escala apagaria o modo claro/escuro salvo
(e vice-versa).

## Limitação conhecida: Sidebar não acompanha troca de escala AO VIVO

A `Sidebar` tem a largura travada em pixels fixos desde a construção (`pack_propagate(False)`,
ver ADR-0040, necessário pra imagem customizada não encostar na borda). Testado e confirmado:
- **Abrir o app já com uma escala salva funciona perfeito** — `ctk.set_widget_scaling()` roda
  antes de qualquer widget existir (`IteradorApp.__init__`), então a Sidebar já nasce com a
  largura certa pra a escala ativa.
- **Trocar a escala com o app já aberto** deixa o texto dos itens de navegação cortado até
  reiniciar o app (ou trocar de novo) — mesmo chamando `on_visuals_changed`/`rebuild_ui()` pra
  reconstruir a Sidebar do zero com a escala nova já ativa, ela nasce na largura antiga de
  qualquer forma; não identifiquei a causa exata dentro do CustomTkinter (parece um problema real
  da lib, não do código do Iterador — o resto da UI reescala perfeitamente na hora, só a largura
  da Sidebar trava). Aceito como limitação conhecida por ora — a troca de escala em si funciona e
  persiste corretamente, só o texto do menu lateral pode ficar visualmente cortado até a próxima
  vez que o app abrir.

## Consequências

- `theme.UI_SCALE_OPTIONS`/`DEFAULT_UI_SCALE` — novas constantes, mesmo padrão de
  `APPEARANCE_MODES`.
- Testado (Xvfb): aplicar 150% ao vivo reescala corretamente cards, botões, texto, gráficos;
  persistência confirmada lendo `preferences.json` e reabrindo o app (abre já em 150%, Sidebar
  com a largura certa desde o início — a limitação acima só afeta a troca ao vivo).
