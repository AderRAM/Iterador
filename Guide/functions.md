# Referência da API pública

A UI só deve depender do que está documentado aqui — não do interior do Backend. Se você
(humano ou IA) precisa de algo que não está nesta lista, é sinal de que `Application` precisa
crescer, não de importar `storage/`/`sync/` direto na UI.

## `iterador_core` (módulo pybind11, `Backend/src/bindings/`)

### `Money` (`bind_core.cpp`)
- `Money(cents: int, currency: str)` — construtor.
- `.cents -> int`, `.currency -> str` — propriedades.
- Operadores: `+`, `-`, comparação (`==`, `<`, ...). Levanta erro se as moedas forem diferentes.

### `Investment` (`bind_core.cpp`)
- Campos: `id: str`, `name: str`, `type: str` (texto livre), `current_value: Money`,
  `yield_rate: float`, `fees_rate: float`, `selic_percentage: float`.
- **`yield_rate`** = rentabilidade fixa (%) — só faz sentido para investimento **prefixado**
  (taxa fixa combinada, ex. "12% ao ano"). Deixe 0 para investimentos pós-fixados.
- **`selic_percentage`** = quanto rende em relação à Selic/CDI (ex. 100 = 100% do CDI, como a
  Caixinha Nubank) — é o que define o rendimento de investimentos pós-fixados, não `yield_rate`.
- Não existe `Account`/`AccountType` no Iterador — ver
  [ADR-0007](decisions/0007-remove-account-add-investment.md). Não há conceito de múltiplas
  contas, só uma carteira única implícita.

### `Category` (`bind_core.cpp`)
- Campos: `id: str`, `name: str`, `kind: CategoryKind` (`INCOME` ou `EXPENSE`).
- O C++ não valida nome contra lista fixa nenhuma — `CategoryRepository::findOrCreateByName`
  acha ou cria a categoria por qualquer nome vindo de Python (ver `Application.createTransaction`).
  A restrição "só estes nomes" é inteiramente da UI: 5 fixas em `backend_bridge.py` + categorias
  personalizadas com nome/tipo/comportamento/cor geridas em Configurações
  (`UI/iterador_ui/custom_categories.py`, ver ADR-0028/0030).

### `Transaction` (`bind_core.cpp`)
- Campos: `id: str`, `category_id: str`, `category_name: str` (só leitura, via `JOIN` — uma das 5
  fixas, `"Essencial"`/`"Lazer"`/`"Investimento"` (despesa) ou `"Ativa"`/`"Passiva"` (receita, ver
  ADR-0014), ou uma categoria personalizada criada em Configurações, ver ADR-0028),
  `type: TransactionType` (`INCOME`/`EXPENSE`/`TRANSFER`), `status: TransactionStatus`
  (`PENDING`/`PAID`), `amount: Money` (sinal já embutido: negativo = despesa), `description: str`,
  `occurred_at: str` (`"YYYY-MM-DD"`, só data — ver ADR-0011), `investment_id: str` (`""` =
  nenhum — presente quando a categoria tem comportamento "Investimento", ver ADR-0014/0028),
  `sort_order: float` (ordem manual de exibição — maior aparece mais acima na lista, substitui
  `occurred_at` como critério principal de `list_transactions()`; arrastar na UI reatribui esse
  valor por indexação fracionária, ver ADR-0033), `is_recurring: bool` (fixada/ícone de pin — ao
  criar um mês novo, é clonada automaticamente pra dentro dele; o clone em si nasce `False`, ver
  ADR-0034).

### `Budget` (`bind_core.cpp`)
- Meta de economia, não limite de gasto — ver [ADR-0017](decisions/0017-savings-goal-budgets.md).
- Campos: `id: str`, `name: str`, `target_value: Money` (valor total do item), `months: int`
  (em quantos meses dividir), `investment_id: str` (`""` = nenhum, só informativo — não move
  valores), `created_at: str` (`"YYYY-MM-DD"`, mesmo padrão de `Transaction.occurred_at`).
- O aporte mensal necessário (`target_value.cents / months`) não é um campo — é sempre calculado
  na UI a partir dos dois campos.

### `Application` (`bind_app.cpp`, implementa `Backend/src/app/Application.hpp`)
- `Application(db_path: str)` — abre (ou cria) o banco SQLite em `db_path` e roda migrations pendentes.
- `list_investments() -> list[Investment]` — **pronto**, lê via `InvestmentRepository`.
- `create_investment(name, type, current_value_cents, currency, yield_rate, fees_rate, selic_percentage) -> Investment` — **pronto**.
- `update_investment(id, name, type, current_value_cents, currency, yield_rate, fees_rate, selic_percentage) -> Investment` — **pronto**, sobrescreve todos os campos; lança erro se `id` não existir.
- `delete_investment(id) -> None` — **pronto** (ver ADR-0031). Antes de apagar, desvincula (não apaga) qualquer transação/orçamento que apontava pra esse investimento — `investment_id` vira `""`/NULL na tabela deles, mesmo estado de "nenhum investimento" (ADR-0022); sem isso a FK (`foreign_keys=ON`) barraria a remoção. Lança erro se `id` não existir.
- `list_transactions() -> list[Transaction]` — **pronto**.
- `create_transaction(description, category_name, type, amount_cents, currency, status, occurred_at_date, investment_id) -> Transaction` — **pronto**; acha/cria a categoria pelo `category_name` (fixa por Tipo, ver ADR-0014). `occurred_at_date` é `"YYYY-MM-DD"` — quem decide o padrão (dia atual) é a UI. `investment_id` (`""` = nenhum) ajusta o valor do investimento ligado — delta = `amount_cents` direto, **sem inverter o sinal** (despesa categoria Investimento = saque, subtrai; receita categoria Passiva = aporte/rendimento, soma — ver ADR-0014).
- `update_transaction(id, description, category_name, type, amount_cents, currency, status, occurred_at_date, investment_id) -> Transaction` — **pronto**; sobrescreve todos os campos; reverte o efeito no investimento antigo antes de aplicar o novo; lança erro se `id` não existir.
- `set_transaction_status(id, status) -> Transaction` — **pronto**; alterna pago/pendente sem mexer nos outros campos (usado pelo botão de status na lista, ver ADR-0011).
- `update_transaction_sort_order(id, sort_order: float) -> Transaction` — **pronto**; só grava a ordem manual de exibição (calculada na UI a partir dos vizinhos do arrasto, ver ADR-0033), sem lógica de negócio; lança erro se `id` não existir.
- `update_transaction_recurring(id, is_recurring: bool) -> Transaction` — **pronto**; só grava a marca de fixada/recorrente (ícone de pin, ver ADR-0034), sem lógica de negócio — a clonagem pro mês novo é decidida pela UI; lança erro se `id` não existir.
- `delete_transaction(id) -> None` — **pronto**; lança erro se `id` não existir.
- `list_budgets() -> list[Budget]` — **pronto**.
- `create_budget(name, target_value_cents, currency, months, investment_id) -> Budget` — **pronto**.
- `update_budget(id, name, target_value_cents, currency, months, investment_id) -> Budget` — **pronto**; sobrescreve todos os campos exceto `created_at`; lança erro se `id` não existir.
- `delete_budget(id) -> None` — **pronto**; lança erro se `id` não existir.
- `start_sync() -> None` — **stub**, inicia `SyncEngine` (hoje não faz nada de rede ainda).
- `stop_sync() -> None` — **stub**.
- `sync_status() -> SyncStatus` — **stub**, retorna status vazio/desabilitado.

## `UI/iterador_ui/backend_bridge.py`

Ponto único que importa `iterador_core` — todo o resto da UI passa por aqui, nunca importa o
módulo compilado diretamente.

- `open_database(path: str) -> None` — cria a instância global de `Application`.
- `list_investments() -> list[Investment]` — repassa para `Application.list_investments()`.
- `create_investment(name, type_, current_value_cents, currency, yield_rate, fees_rate, selic_percentage) -> Investment` — repassa.
- `update_investment(investment_id, name, type_, current_value_cents, currency, yield_rate, fees_rate, selic_percentage) -> Investment` — repassa.
- `delete_investment(investment_id) -> None` — repassa.
- `list_transactions() -> list[Transaction]` — repassa.
- `create_transaction(description, category_name, type_, amount_cents, currency, status, occurred_at_date, investment_id="") -> Transaction` — repassa.
- `update_transaction(transaction_id, description, category_name, type_, amount_cents, currency, status, occurred_at_date, investment_id="") -> Transaction` — repassa.
- `set_transaction_status(transaction_id, status) -> Transaction` — repassa.
- `update_transaction_sort_order(transaction_id, sort_order: float) -> Transaction` — repassa (ordem manual de exibição, arrastar na lista, ver ADR-0033).
- `update_transaction_recurring(transaction_id, is_recurring: bool) -> Transaction` — repassa (fixada/ícone de pin, ver ADR-0034).
- `delete_transaction(transaction_id) -> None` — repassa.
- `list_budgets() -> list[Budget]` — repassa.
- `create_budget(name, target_value_cents, currency, months, investment_id="") -> Budget` — repassa.
- `update_budget(budget_id, name, target_value_cents, currency, months, investment_id="") -> Budget` — repassa.
- `delete_budget(budget_id) -> None` — repassa.
- `expense_category_names() -> list[str]` / `income_category_names() -> list[str]` — as 5 fixas
  (`["Essencial", "Lazer", "Investimento"]`/`["Ativa", "Passiva"]`, ver ADR-0014) mescladas com as
  categorias personalizadas do tipo correspondente (`custom_categories.py`, ver ADR-0028). Antes
  eram constantes (`EXPENSE_CATEGORY_NAMES`/`INCOME_CATEGORY_NAMES`); viraram função pra sempre
  refletir categorias criadas em Configurações sem precisar reiniciar o app.
- `investment_linked_categories() -> set[str]` — `{"Investimento", "Passiva"}` mais qualquer
  categoria personalizada marcada como "comportamento Investimento" — usado pra saber quando
  mostrar o seletor de investimento na UI. Também era constante (`INVESTMENT_LINKED_CATEGORIES`).
- `fixed_category_names() -> set[str]` — as 5 categorias fixas, usado só por
  `custom_categories.add_custom_category()` pra impedir nome duplicado.
- `transaction_enums() -> dict` — retorna `{"income", "expense", "paid", "pending"}` mapeados
  para os valores reais de `TransactionType`/`TransactionStatus`, pra UI não importar
  `iterador_core` diretamente.
- `sync_status() -> dict` — repassa `Application.sync_status()` já convertido para uso simples na UI.

## `UI/iterador_ui/undo_stack.py` / `transaction_commands.py`

Ver [ADR-0013](decisions/0013-undo-redo-and-ui-polish.md). `UndoStack` é genérica
(`.push(command)`, `.undo()`, `.redo()`, `.can_undo()`, `.can_redo()`); os comandos concretos
(`CreateTransactionCommand`, `UpdateTransactionCommand`, `DeleteTransactionCommand`,
`ToggleStatusCommand`, `ReorderTransactionCommand` — arrastar na lista, ver ADR-0033,
`TogglePinCommand` — fixar/desfixar recorrente, ver ADR-0034) ficam em `transaction_commands.py`
e só chamam `backend_bridge` — não mexem em widgets. Exceções: `RemoveMonthCommand` (ver
ADR-0019) também repõe o bookkeeping do `MonthSelector` — remove/recria todas as transações de
um mês de uma vez, um único item no desfazer; `ResetTransactionOrderCommand` (ver ADR-0033)
reatribui `sort_order` de várias transações de uma vez — botão "Resetar posições" no cabeçalho
da lista, volta a ordem manual do mês pra ordem padrão por data, também um único item no
desfazer; `AddMonthCommand` (ver ADR-0034) — inversa de `RemoveMonthCommand`, criada por
`DashboardView._on_month_added` quando "+ Mês" clona pelo menos uma transação fixada, um único
item cobrindo todas as clonagens + o bookkeeping do mês.

## `UI/iterador_ui/widgets/month_selector.py`

Ver [ADR-0016](decisions/0016-monthly-transaction-navigation.md),
[ADR-0018](decisions/0018-bounded-month-navigation-and-add-month.md) e
[ADR-0019](decisions/0019-remove-month-with-undo.md).

- `current_month() -> str` — mês atual em `"YYYY-MM"`.
- `month_label(month_str) -> str` — rótulo PT-BR, ex. `"Setembro/2026"`.
- `MonthSelector(master, on_select, on_remove_month)` — faixa horizontal rolável de meses +
  setas `◀`/`▶` + botões "+ Mês"/"Remover mês". `update_months(available_months: set[str])`
  reconstrói a faixa; `selected_month() -> str`. Navegação por índice na lista de meses
  conhecidos (com lançamento, adicionados manualmente, ou o selecionado) — `◀`/`▶` ficam
  `disabled` nas pontas, não avançam pra mês nenhum. `on_remove_month(month_str)` é chamado
  quando o usuário clica "Remover mês" — quem decide o que fazer (confirmar, apagar
  transações) é `DashboardView`, não o widget.
- Métodos de bookkeeping usados por `RemoveMonthCommand` (ver ADR-0019):
  `is_extra_month(month_str) -> bool`, `add_extra_month(month_str)`, `remove_month(month_str)`
  (só tira de `_extra_months`, não mexe em seleção), `neighbor_of(month_str) -> str` (mês
  vizinho mais próximo, pra decidir pra onde ir depois de remover o selecionado),
  `force_select(month_str)` (troca a seleção sem disparar `on_select`).

## `UI/iterador_ui/widgets/add_month_dialog.py`

Ver [ADR-0018](decisions/0018-bounded-month-navigation-and-add-month.md).

- `parse_month_input(text) -> str | None` — aceita `"MM/AAAA"` ou `"AAAA-MM"`, retorna
  `"YYYY-MM"` ou `None` se não bater com nenhum dos dois formatos.
- `AddMonthDialog(master, on_add)` — diálogo modal com campo de texto; ao submeter válido, chama
  `on_add(month_str)` e fecha.

## `UI/iterador_ui/widgets/line_chart.py`

Ver [ADR-0021](decisions/0021-cdi-history-from-bcb.md).

- `LineChart(master)` — gráfico de linha genérico (Canvas puro, mesmo estilo do
  `ConsumptionChart`). `update_data(points: list[tuple[str, float]])` desenha a série inteira e
  destaca o ponto de valor mínimo (vermelho) e máximo (verde) com rótulo. Não é específico de
  CDI — reutilizável pra qualquer série temporal futura.

## `UI/iterador_ui/widgets/confirm_dialog.py`

Ver [ADR-0019](decisions/0019-remove-month-with-undo.md).

- `ConfirmDialog(master, title, message, on_confirm, confirm_text="Confirmar")` — diálogo modal
  genérico de confirmação (Cancelar/Confirmar); ao confirmar, chama `on_confirm()` e fecha.
  Reutilizável para qualquer ação destrutiva futura, não só remover mês.

## `UI/iterador_ui/version.py`

`APP_VERSION: str` — exibida em `SettingsView`. Atualizar conforme marcos relevantes, não a
cada mudança pequena (ver CLAUDE.md).

## `UI/iterador_ui/preferences.py`

`~/.iterador/preferences.json`, round-trip completo (ver ADR-0044 — antes só tinha
`appearance_mode` e sobrescrevia o arquivo inteiro a cada save).

- `load_appearance_mode() -> str` / `save_appearance_mode(mode: str) -> None`.
- `load_ui_scale() -> float` / `save_ui_scale(scale: float) -> None` — uma de
  `theme.UI_SCALE_OPTIONS` (0.9/1.0/1.1/1.25/1.5); `theme.DEFAULT_UI_SCALE` (1.0) se ausente/
  inválido.

## `UI/iterador_ui/sidebar_image.py`

Ver [ADR-0037](decisions/0037-custom-sidebar-logo-image-overlay.md)/
[ADR-0040](decisions/0040-sidebar-fixed-width-and-final-logo-size.md) (ADR-0036/0038/0039
superseded) e [ADR-0045](decisions/0045-bundled-default-sidebar-logo.md). Logo customizado da
Sidebar — aparece ACIMA de `TriangleHeading`, nunca no lugar dele.

- `get_logo_path() -> Path | None` — `~/.iterador/sidebar_logo.png` se existir, senão `None`.
  Usado só por `settings_view.py` pra saber se existe uma imagem enviada pelo usuário
  especificamente (habilitar botão "Remover imagem", texto de status) — não é o que decide o
  que a Sidebar exibe (ver `get_display_image()`).
- `set_custom_logo(source_path: str) -> None` — abre a imagem enviada (qualquer formato que o
  Pillow lê), ajusta mantendo proporção pra `LOGO_SIZE` (174×130px, o maior possível sem
  encostar na borda da Sidebar — que agora tem a largura travada de verdade, ver ADR-0040) com
  borda preta de 4px, sempre salva como
  PNG. Levanta `SidebarImageError` (mensagem pronta pra mostrar ao usuário) se o arquivo for
  inválido/corrompido.
- `remove_custom_logo() -> None` — apaga o arquivo customizado se existir (no-op se não existir);
  cai de volta na imagem padrão embutida se houver uma, não direto pro mosaico.
- `get_display_image() -> Image.Image | None` — usado por `sidebar.py`; imagem pronta pra
  exibir, já com a moldura preta: a do usuário (`get_logo_path()`) se existir, senão a padrão
  embutida em `UI/assets/Atlas.<ext>` (nome fixo "Atlas", qualquer extensão que o Pillow leia,
  emoldurada em memória a cada chamada — nunca gravada em disco, `assets/` é o pacote do app),
  senão `None` (só o mosaico) — ver ADR-0045.
- `has_bundled_default() -> bool` — só pro texto de status em Configurações distinguir "usando
  imagem personalizada" / "usando a imagem padrão do Iterador" / "usando o mosaico".

## `UI/iterador_ui/market_data.py`

Única chamada de rede da UI para fora do protocolo de sync — ver
[ADR-0008](decisions/0008-fetch-selic-rate-from-bcb.md) e
[ADR-0021](decisions/0021-cdi-history-from-bcb.md).

- `fetch_current_selic_rate(timeout=5.0) -> SelicRate | None` — busca a Meta Selic (série 432 do
  BCB) via HTTP. Retorna `None` em qualquer falha de rede (nunca lança exceção — o app funciona
  offline). `SelicRate` tem `percent_per_year: float` e `reference_date: str`.
- `fetch_current_cdi_rate(timeout=5.0) -> CdiRate | None` — busca o CDI anualizado atual (série
  4389 do BCB, % a.a.). Mesma tolerância a falha; `CdiRate` tem os mesmos dois campos que
  `SelicRate`.
- `fetch_cdi_history(years=3, timeout=10.0) -> list[tuple[str, float]] | None` — histórico do
  CDI anualizado dos últimos `years` anos (série 4389, intervalo `dataInicial`/`dataFinal`),
  como lista de `(data "dd/mm/aaaa", valor)` em ordem cronológica. `None` em qualquer falha.

## `UI/iterador_ui/theme.py`

Ver [ADR-0020](decisions/0020-color-profile-system.md). Todas as cores vêm de um "perfil" ativo
(dicionário) — o resto da UI continua lendo `theme.CONSTANTE` do jeito de sempre, então nada
muda pra quem só usa as cores.

- `apply_profile(name="default") -> None` — troca o perfil de cor ativo, recalcula
  `CATEGORY_COLORS` e reatribui todas as constantes no módulo. Chamado uma vez no import
  (`apply_profile("default")` no fim do arquivo); pode ser chamado de novo em runtime pra trocar
  de perfil (sem UI própria pra isso ainda).
- `available_profiles() -> list[str]` / `current_profile() -> str`.
- Constantes de cor (`BRICK_EMBER`, `INDIGO`, `CARBON_BLACK`, `DEEP_SAFFRON`, `SUNFLOWER_GOLD`,
  `ELECTRIC_BLUE`) e helper de estilo `outline_button_style()` (fundo transparente, borda fina em
  `BORDER_ACCENT`, cantos arredondados — usado em Desfazer/Refazer). O logo/título "Iterador" na
  sidebar não usa mais cor chapada (`heading_style()`, removido) — é `TriangleHeading`, mosaico
  triangular de tons de laranja com borda branca por letra, ver ADR-0025.
- `VALUE_INCOME` (verde claro) / `VALUE_EXPENSE` (vermelho puro) — só para exibir valores
  monetários de receita/despesa (lista de lançamentos e "Fim do mês", `DashboardView`).
  Diferentes de `ACCENT_INCOME`/`ACCENT_EXPENSE` (Indigo/Brick Ember), que continuam sendo as
  cores de destaque usadas em botões no resto da UI. Ver
  [`architecture.md`](architecture.md#identidade-visual-ui).
- `CATEGORY_COLORS` (dict) / `category_color(name) -> str` — cor por categoria (ver ADR-0014),
  usada tanto na lista de lançamentos quanto nas fatias do `ConsumptionChart`. Categoria sem
  entrada em `CATEGORY_COLORS` (qualquer personalizada, ver ADR-0028) cai numa paleta auxiliar de
  8 tons por hash determinístico do nome (bytes UTF-8, não `hash()` embutido — esse é randomizado
  por processo).
  Sempre retorna uma cor resolvida (não-tupla claro/escuro).
- `BORDER_NEUTRAL` (tupla, separador discreto) / `BORDER_ACCENT` (azul, separador
  estrutural/borda de botão de contorno) / `NAV_INDICATOR_ACTIVE` (vermelho, página ativa na
  sidebar) / `ROW_SEPARATOR` (verde-azulado, separador de cada lançamento na lista) — ver
  ADR-0020.
- `THEME_SWITCH_DARK_COLOR`/`THEME_SWITCH_LIGHT_COLOR` — cores do switch de tema da sidebar
  (invertidas de propósito, ver ADR-0013).

## `UI/iterador_ui/widgets/divider.py`

Ver [ADR-0020](decisions/0020-color-profile-system.md).

- `Divider(master, color, thickness=2, orientation="horizontal")` — `CTkFrame` fino sem
  conteúdo; `orientation="vertical"` usa `width` em vez de `height`. Cor sempre vem de
  `theme.py`, nunca hardcoded em quem usa.
