# 0020 — Sistema de perfis de cor + separadores estruturais na UI

Status: Aceito

## Contexto

O usuário mandou um print da tela Início com 7 anotações numeradas pedindo elementos visuais
novos: (1) uma barrinha branca embaixo de cada item da sidebar que vira vermelha na página atual
selecionada — não existia **nenhum** indicador de página ativa até agora; (2) as mesmas barrinhas
servindo de separador entre os itens da sidebar; (3) um separador azul isolando o cabeçalho
"Início" do resto do conteúdo; (4) um separador azul vertical entre o gráfico de consumo e o
card "Total do mês"; (5) um separador fino, num verde-azulado, embaixo de cada lançamento da
lista; (6) dois separadores azuis isolando a barra de cabeçalho de colunas (Data/Descrição/
Categoria/etc.) da lista; (7) botões "Desfazer"/"Refazer" com cantos arredondados e borda fina
azul. Pediu explicitamente pra isso ser construído "de forma que fique fácil pra editar cores no
futuro e adicionar perfis de cores" — ou seja, a parte estrutural do pedido é tanto os elementos
visuais quanto a infraestrutura por trás deles.

## Decisão

### Sistema de perfis de cor (`theme.py`)

- `theme.py` virou um registro de perfis: cada perfil é uma função sem argumento
  (`_default_palette()`) que devolve um dicionário `{NOME_DA_CONSTANTE: valor}` — todas as cores
  do app num só lugar, incluindo as tuplas (claro, escuro) já prontas. `_PROFILES` mapeia nome →
  função. `apply_profile(name)` calcula o dicionário do perfil (mais `CATEGORY_COLORS`, derivado
  dele) e faz `globals().update(palette)` — empurra tudo pro nível de módulo.
- Todo o resto da UI continua fazendo `from iterador_ui import theme` e lendo `theme.CONSTANTE`
  (nunca `from iterador_ui.theme import CONSTANTE` — confirmado por busca no código antes dessa
  mudança) — então trocar de perfil com `theme.apply_profile("outro_nome")` já reflete em
  qualquer view sem precisar reimportar nada, porque `theme.CONSTANTE` é sempre um lookup no
  dicionário do módulo, nunca um valor congelado em import.
- Adicionar um perfil novo no futuro = copiar `_default_palette`, ajustar os valores, registrar
  em `_PROFILES` com um nome. Não implementado ainda: nenhuma UI (ex. em Configurações) pra
  trocar de perfil em tempo de execução — só a função `apply_profile()`/`available_profiles()`/
  `current_profile()` já prontas pra quando isso for pedido.
- Novos papéis semânticos adicionados: `BORDER_NEUTRAL` (tupla, separador discreto — branco no
  escuro/cinza no claro), `BORDER_ACCENT` (azul elétrico novo, `ELECTRIC_BLUE` — separadores
  estruturais + borda dos botões de contorno), `NAV_INDICATOR_ACTIVE` (vermelho, indicador de
  página ativa na sidebar), `ROW_SEPARATOR` (verde-azulado, separador de cada lançamento).
- `theme.outline_button_style()` — kwargs prontos pra um botão de contorno (fundo transparente,
  borda 1px em `BORDER_ACCENT`, `corner_radius=10`). Um só lugar pra mudar a aparência desse
  estilo de botão em todo o app.

### `Divider` (novo widget, `UI/iterador_ui/widgets/divider.py`)

- `CTkFrame` fino sem conteúdo, cor sempre vinda de `theme.py` — nunca hardcoded em quem usa. Um
  parâmetro `orientation` decide se vira uma barra horizontal (`height=thickness`, `pack(fill="x")`
  ou `grid(sticky="ew")`) ou vertical (`width=thickness`, `pack(fill="y")`).

### Onde cada separador entrou

- **Sidebar** (`widgets/sidebar.py`): cada item de navegação agora é um `CTkFrame` com o botão +
  um `Divider(color=theme.BORDER_NEUTRAL, thickness=2)` embaixo. `Sidebar.set_active(view_name)`
  (chamado por `IteradorApp.show_view()` a cada navegação) recolore o `Divider` do item ativo pra
  `theme.NAV_INDICATOR_ACTIVE` (vermelho) e aumenta a espessura pra 3 — resolve os itens 1 e 2 ao
  mesmo tempo, já que descrevem o mesmo elemento visual em dois estados (neutro = separador entre
  abas; vermelho e mais grosso = indicador da página atual).
- **`DashboardView`** (item 3): `Divider(color=theme.BORDER_ACCENT)` logo após o cabeçalho
  "Início"/Desfazer/Refazer.
- **`DashboardView`** (item 4): `Divider(orientation="vertical", color=theme.BORDER_ACCENT)`
  dentro de `top_row`, empacotado depois do `total_card` de propósito — em `pack(side="right")`,
  quem é empacotado por último no lado direito fica mais à esquerda dos anteriores, então isso
  deixa o separador encostado à esquerda do card "Total do mês", não na borda da janela.
- **`DashboardView`** (item 5): a lista de lançamentos passou a usar duas linhas de grid por
  transação (linha de dado + linha de `Divider(color=theme.ROW_SEPARATOR, thickness=2)` logo
  abaixo) — `row = 3 + offset * 2` pros dados, `row + 1` pro separador.
- **`DashboardView`** (item 6): um `Divider(color=theme.BORDER_ACCENT)` antes e depois da linha
  de cabeçalho de colunas (Data/Descrição/Categoria/Status/Valor).
- **`DashboardView`** (item 7): botões "↷ Refazer"/"↶ Desfazer" agora usam
  `**theme.outline_button_style()` em vez de `fg_color=theme.BG_SURFACE` sólido.

## Consequências

- `outline_button_style()` só foi aplicado nos botões explicitamente circulados no print
  (Desfazer/Refazer) — os outros botões do app (Editar/Remover da lista, +Mês/Remover mês,
  +Adicionar, +Nova meta) continuam com o estilo antigo. Aplicar o contorno neles depois é
  trivial (`**theme.outline_button_style()` em vez do `fg_color`/`hover_color` atual), mas não
  foi pedido nesta rodada.
- O separador de 1px inicial (item 5) ficou praticamente invisível na tela — confirmado por
  inspeção direta da geometria dos widgets (existia, `winfo_height() == 1`, mas sem contraste
  perceptível). Subiu pra 2px, mesmo padrão dos separadores azuis estruturais.
- A troca de perfil (`apply_profile()`) não persiste entre execuções nem tem UI própria ainda —
  quando isso for pedido, o próximo passo natural é guardar o nome do perfil ativo em algum
  lugar (ex. um arquivo de config local, já que não tem a ver com dado financeiro do usuário) e
  adicionar um seletor em `SettingsView`.
- Nenhuma mudança de schema/backend — é só UI.
