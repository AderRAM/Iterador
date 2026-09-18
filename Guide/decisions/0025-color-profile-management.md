# 0025 — Sistema de perfis de cor + textura triangular no logo

Status: Aceito

## Contexto

O usuário pediu pra poder trocar a paleta de cores do Iterador sem editar código: criar, editar,
renomear e remover perfis, com o perfil de hoje salvo como `Prizmo_V1` (preservado exatamente
como estava — "a forma atual agrada a mim pessoalmente"). Junto disso:

1. O fundo do "Iterador" na sidebar (Sunflower Gold sólido) usava a mesma cor do botão de tema
   claro/escuro no modo escuro, e o usuário achou pouco a ver com o ícone do app. Amostrei
   `UI/assets/icon.png` de verdade (análise de pixel, não só olhando) — o laranja do ícone é um
   aglomerado de tonalidades (`#F8A000` mais vibrante/frequente até `#D06800` mais escuro), não
   uma cor só — e pediu uma **textura triangular** ("low-poly") no fundo do logo com esse mesmo
   aglomerado, não uma cor sólida nova.
2. Perfis novos devem poder simplificar fundo/frame/borda em 3 cores (Primária/Secundária/
   Terciária) + uma 4ª pro texto estático, pra quem achar o visual padrão colorido/complexo
   demais — **excluindo** valores monetários (verde/vermelho), cor por categoria e badge Pago/A
   pagar, que continuam com a lógica própria de sempre em qualquer perfil.

## Decisão

### Dois "modos" de perfil no mesmo arquivo (`~/.iterador/color_profiles.json`)

- `"detailed"` — só `Prizmo_V1` usa: guarda os ~27 papéis completos que `theme.py` sempre teve
  (fundo/texto claro-escuro, bordas, etc.), exatamente como estavam. Editável só por
  renomear/remover — um formulário com ~27 campos independentes é outro escopo.
- `"simple"` — todo perfil criado pelo usuário: guarda só 4 campos (`static_text`, `primary`,
  `secondary`, `tertiary`), cada um uma cor só (não par claro/escuro — simplificação deliberada,
  quem quer simplificar não deveria precisar acertar duas versões de cada cor).
  `theme._expand_simple_profile()` estica isso pros mesmos papéis estruturais que `Prizmo_V1`
  usa: `primary`→`BG_APP`, `secondary`→`BG_SURFACE`/`BG_PANEL_BLUE`, `tertiary`→
  `BORDER_ACCENT`/`BORDER_NEUTRAL`/`STATUS_BADGE_BORDER`/`ROW_SEPARATOR` (unifica todos os
  acentos de borda hoje independentes numa cor só), `static_text`→`TEXT_PRIMARY`.
- Papéis que **não** fazem parte de nenhum perfil (`theme._fixed_roles()`): marca (Brick Ember,
  Indigo), valores monetários, cor por categoria (`CATEGORY_COLORS`/`CATEGORY_LABEL_COLORS`),
  `NAV_INDICATOR_ACTIVE`, cores do botão de tema. Sempre as mesmas, em qualquer perfil.

### Textura triangular (`UI/iterador_ui/widgets/triangle_heading.py`)

- `TriangleHeading`, um `tkinter.Canvas` (mesmo padrão de `ConsumptionChart`/`LineChart`) — grade
  de células, cada uma virando 2 triângulos, cada um com uma cor sorteada dentro do aglomerado
  real do ícone (`ICON_ORANGE_CLUSTER`, os hex amostrados) mais uma pequena variação de brilho
  (`_jitter`), pra ter mais variedade sem sair da família de laranjas. Sorteio acontece uma vez
  na criação do widget — reconstrução da Sidebar (troca de perfil, ver abaixo) gera um mosaico
  novo, fica igual durante o resto do uso.
- Sem cantos arredondados (o `CTkLabel` antigo tinha `corner_radius=6`) — vira um retângulo reto;
  recortar triângulos dentro de um raio arredondado seria bem mais trabalho por pouco ganho.
- `theme.SUNFLOWER_GOLD` em si também mudou de `#FFC72C` pro laranja mais frequente do ícone
  (`#F8A000`) — usado nos lugares que continuam com cor sólida (borda do card Total do mês,
  botão de tema no escuro), já que o usuário reclamou dessa cor nos dois lugares, não só no logo.

### Aplicar um perfil em runtime — `IteradorApp.rebuild_ui()`

Mudar o valor de `theme.BG_APP` etc. não recolore widgets já construídos — cada CTkFrame/CTkLabel
guardou a tupla antiga na criação, e só reage a `ctk.set_appearance_mode()` (claro/escuro), não a
`theme.py` mudar de valor por baixo. `rebuild_ui()` destrói e recria a Sidebar + a view atual
(mesmo par destroy+recria que `show_view()` já fazia pra trocar de aba, só que pros dois de uma
vez) — chamado depois de aplicar, editar-e-salvar, renomear (se o renomeado for o ativo) ou
remover (se o removido era o ativo) um perfil.

### `UI/iterador_ui/color_profiles.py` — CRUD

`list_profiles`/`get_active_profile_name`/`get_profile`/`set_active_profile`/`create_profile`/
`update_profile`/`rename_profile`/`delete_profile`. `delete_profile` recusa apagar o último
perfil restante (`ProfileError`); se o perfil removido for o ativo, escolhe outro sozinho.
`update_profile` recusa perfil `"detailed"` (só `"simple"` é editável).

### UI — nova seção "Perfis de cor" em `SettingsView`

Seletor + "Aplicar", mais "Novo perfil"/"Editar"/"Renomear"/"Remover" (remove com
`ConfirmDialog` já existente). `ColorProfileDialog` (criar/editar, 4 campos com
`tkinter.colorchooser.askcolor()` — biblioteca padrão, sem dependência nova) e
`RenameProfileDialog` (separado, porque renomear precisa funcionar pra perfil "detailed" também,
que não tem os 4 campos de cor).

## Consequências

- Um perfil "simple" usa a mesma cor estrutural nos dois temas claro/escuro (não par
  claro/escuro) — trocar de tema com um perfil simples ativo não muda fundo/borda/texto
  estático, só os papéis fixos que ainda diferem por tema internamente (nenhum, na prática,
  já que os fixos não têm par claro/escuro). Aceito como parte da simplificação pedida.
- Editar um perfil "detailed" (`Prizmo_V1`) inteiro não tem UI ainda — só dá pra
  renomear/remover. Se isso for pedido, precisa de um formulário bem maior (~27 campos) ou
  converter pra "simple" primeiro.
- `TriangleHeading` sorteia um mosaico novo a cada `Sidebar` reconstruída (troca de tema
  claro/escuro **não** reconstrói a Sidebar, só perfil novo via `rebuild_ui()` reconstrói) — o
  mosaico não muda ao alternar claro/escuro, só ao trocar de perfil.
