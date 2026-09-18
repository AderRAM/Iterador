# Mapa de arquivos

Status: `pronto` (implementado e funcional) · `stub` (existe, assinatura/estrutura sem lógica
completa) · `planejado` (ainda não existe, descrito no roadmap).

## Raiz

| Caminho | Responsabilidade | Status |
|---|---|---|
| `App/` | App Android (Kotlin/Gradle) — não tocar nesta fase | pronto (template) |
| `Guide/` | Documentação viva do projeto | pronto |
| `Backend/` | Núcleo C++ + bindings pybind11 | ver abaixo |
| `UI/` | Interface CustomTkinter | ver abaixo |
| `scripts/` | Scripts de setup/build/run/instalação do atalho | pronto |
| `CLAUDE.md` | Contexto para assistentes de IA | pronto |
| `README.md` | Entrada do projeto, aponta pro Guide | pronto |
| `.gitignore` | Ignora builds, venv, bancos de dev | pronto |

## `Backend/`

| Caminho | Responsabilidade | Status |
|---|---|---|
| `CMakeLists.txt` | Build do módulo `iterador_core` | pronto |
| `cmake/Dependencies.cmake` | Resolve pybind11 e SQLite (FetchContent) | pronto |
| `src/core/Money.hpp/.cpp` | Valor monetário (centavos + moeda), aritmética | pronto |
| `src/core/Id.hpp` | Alias de ID + geração de UUID | pronto |
| `src/core/Timestamp.hpp` | Alias de timestamp + helpers ISO-8601 + `fromDateString()` | pronto |
| `src/core/Investment.hpp` | Struct de investimento (nome, tipo, valor, rentabilidade, taxas, % Selic) | pronto |
| `src/core/Category.hpp/.cpp` | Struct de categoria + `CategoryKind` | pronto |
| `src/core/Transaction.hpp/.cpp` | Struct de transação + `TransactionType`, `investmentId`, `categoryName`, `sortOrder` (ordem manual de exibição, ver ADR-0033), `isRecurring` (fixada/ícone de pin, ver ADR-0034) | pronto |
| `src/core/Budget.hpp` | Struct de meta de economia (name, targetValue, months, investmentId) — ver ADR-0017 | pronto |
| `src/storage/Database.hpp/.cpp` | RAII sobre SQLite, migrations, transação | pronto |
| `src/storage/migrations/0001_init.sql` | Schema inicial (investments, categories, transactions, budgets, operation_log) — **nunca editar** | pronto |
| `src/storage/migrations/0002_link_transaction_investment.sql` | Adiciona `transactions.investment_id` — **nunca editar** | pronto |
| `src/storage/migrations/0003_redesign_budgets_as_goals.sql` | Redesenha `budgets` de limite de gasto para meta de economia (DROP+CREATE, seguro pois tabela nunca teve dado real — ver ADR-0017) — **nunca editar** | pronto |
| `src/storage/migrations/0004_add_transaction_sort_order.sql` | Adiciona `transactions.sort_order` (ordem manual de exibição, arrastar na lista) + backfill reproduzindo a ordem por data de antes — ver ADR-0033 — **nunca editar** | pronto |
| `src/storage/migrations/0005_add_transaction_recurring_flag.sql` | Adiciona `transactions.is_recurring` (fixada/ícone de pin, clonada pro mês novo — ver ADR-0034) — **nunca editar** | pronto |
| `src/storage/InvestmentRepository.hpp/.cpp` | CRUD de investimentos, incl. `update()`/`remove()` (ver ADR-0031) | pronto |
| `src/storage/CategoryRepository.hpp/.cpp` | CRUD de categorias + `findOrCreateByName()` | pronto |
| `src/storage/TransactionRepository.hpp/.cpp` | CRUD de transações (com `investment_id` + `JOIN categories`), data editável, `setStatus()`, `updateSortOrder()` (ordem manual, ver ADR-0033), `updateRecurring()` (fixada/pin, ver ADR-0034), `update()`, `remove()`, `clearInvestmentLink()` (ver ADR-0031) | pronto |
| `src/storage/BudgetRepository.hpp/.cpp` | CRUD de metas de economia (`listAll`/`findById`/`create`/`update`/`remove`/`clearInvestmentLink`) — ver ADR-0017/0031 | pronto |
| `src/storage/OperationLog.hpp/.cpp` | Log de operações: `append()` grava (pronto), `applyRemoteOperation()` é stub | pronto (append) / stub (apply) |
| `src/sync/net/PlatformSocket.hpp/.cpp` | Abstração de socket (isola Win/POSIX) | stub |
| `src/sync/IPeerSource.hpp` | Interface comum de descoberta de peers | pronto |
| `src/sync/PeerDiscovery.hpp/.cpp` | Descoberta em LAN via UDP broadcast | stub |
| `src/sync/TailscalePeerSource.hpp/.cpp` | Descoberta via lista `peers.json` | stub |
| `src/sync/SyncProtocol.hpp/.cpp` | Framing/serialização das mensagens de sync | stub |
| `src/sync/HybridLogicalClock.hpp/.cpp` | Relógio híbrido para ordenar operações | stub |
| `src/sync/SyncEngine.hpp/.cpp` | Orquestra descoberta + troca de log em thread própria | stub |
| `src/sync/SyncConfig.hpp` | Configuração do sync (porta, intervalo, nome do device) | pronto |
| `src/app/Application.hpp/.cpp` | Fachada única exposta ao Python, incl. `updateTransactionSortOrder` (ADR-0033) e `updateTransactionRecurring` (ADR-0034) | pronto (investments, transactions, budgets) / stub (sync) |
| `src/bindings/module.cpp` | Ponto de entrada do módulo `iterador_core` | pronto |
| `src/bindings/bind_core.cpp` | Bindings de Money/Investment/Category/Transaction/Budget | pronto |
| `src/bindings/bind_app.cpp` | Bindings de Application | pronto |
| `tests/CMakeLists.txt` | Build dos testes (doctest via FetchContent) | pronto |
| `tests/test_money.cpp` | Testes de `Money` | pronto |

## `UI/`

| Caminho | Responsabilidade | Status |
|---|---|---|
| `main.py` | Ponto de entrada, instancia e roda a app | pronto |
| `requirements.txt` | Dependências Python (customtkinter) | pronto |
| `iterador_ui/theme.py` | Paleta de cores por perfil (`apply_profile`), papéis semânticos, `outline_button_style(strong_border=False)` (ver ADR-0020/0029); cor de Investimento/Passiva é campo por perfil desde a ADR-0047 (Prizmo_V1 roxo, Roze Quartz rosa — ver ADR-0043/0047), `CATEGORY_NO_OUTLINE` (sem contorno preto nessas duas, ver ADR-0042/0047); `UI_SCALE_OPTIONS`/`DEFAULT_UI_SCALE` (ver ADR-0044) | pronto |
| `iterador_ui/app.py` | Janela raiz, navegação entre views, atualiza indicador de página ativa na sidebar; força `DrawEngine.preferred_drawing_method = "polygon_shapes"` (bem mais rápido que o padrão do Linux/Windows, ver ADR-0049) | pronto |
| `iterador_ui/backend_bridge.py` | Único ponto que importa `iterador_core` | pronto |
| `iterador_ui/market_data.py` | Busca Selic e CDI (atual + histórico) na API do Banco Central (ver ADR-0008/0021) | pronto |
| `iterador_ui/version.py` | `APP_VERSION`, exibida em Configurações | pronto |
| `iterador_ui/preferences.py` | Preferências persistidas em `~/.iterador/preferences.json` (arquivo próprio, não o banco) — tema claro/escuro e escala da interface (round-trip completo, ver ADR-0044) | pronto |
| `iterador_ui/color_profiles.py` | CRUD de perfis de cor, persistido em `~/.iterador/color_profiles.json` — ver ADR-0025; sempre garante que `Prizmo_V1` e `Roze Quartz` (tema rosa/rose gold, ver ADR-0041) existem como opção, mesmo em arquivos já existentes de antes desses perfis; `_backfill_investment_category_fields()` faz o mesmo pros 3 campos de cor de Investimento/Passiva em perfis "detailed" já persistidos de antes da ADR-0047 | pronto |
| `iterador_ui/sidebar_image.py` | Logo customizado da Sidebar — imagem enviada pelo usuário ajustada (mantendo proporção) e emoldurada em preto, sempre salva como `~/.iterador/sidebar_logo.png`; sem imagem do usuário, cai na imagem padrão embutida `UI/assets/Atlas.<ext>` (emoldurada na hora, sem gravar em disco) — ver ADR-0037/0040/0045 (ADR-0036/0038/0039 superseded) | pronto |
| `iterador_ui/custom_categories.py` | CRUD de categorias personalizadas (nome, tipo Despesa/Receita, comportamento Investimento/Comum, cor editável — ver ADR-0030), persistido em `~/.iterador/custom_categories.json` — ver ADR-0028 | pronto |
| `iterador_ui/spreadsheet_import.py` | Leitura/mapeamento da planilha Excel do usuário (`parse_workbook`, sem tocar no banco) — ver ADR-0023 | pronto |
| `iterador_ui/statement_import.py` | Leitura de extrato Nubank CSV (conta/PIX ou fatura de cartão, `parse_statement`, sem tocar no banco) — ver ADR-0024 | pronto |
| `iterador_ui/data_export.py` | Exporta investimentos/lançamentos/metas pra um `.zip` (CSV por entidade + metadata) | pronto |
| `iterador_ui/undo_stack.py` | Pilha genérica de desfazer/refazer (comandos com `.undo()`/`.redo()`) | pronto |
| `iterador_ui/transaction_commands.py` | Comandos concretos de desfazer/refazer para transações, incl. `TogglePinCommand`/`AddMonthCommand` (fixar/clonar recorrentes, ver ADR-0034) | pronto |
| `iterador_ui/views/dashboard_view.py` | Início: seletor de mês (navegação infinita, ver ADR-0016), contador discreto de lançamentos, gráfico de consumo por categoria + comparativo mensal por categoria dos últimos 6 meses (ver ADR-0029), total do mês, cards de receitas/despesas/saldo pago, lista rolável em colunas (add/editar/remover/status/pin/desfazer/lista de compras) com separadores estruturais/por linha (ver ADR-0020), alça de arrastar pra reordenar manualmente (tipo playlist, com fundo sólido pra linha nunca "perder forma" enquanto flutua/desliza, auto-scroll perto da borda visível) + cabeçalho "Data" clicável pra inverter a ordem por data + botão "Resetar posições" (volta a ordem manual do mês pra ordem por data, desfazível — ver ADR-0033) + ícone de pin entre Data e Descrição (fixa transação recorrente, clonada automaticamente ao criar mês novo — ver ADR-0034), coluna Categoria com `OutlinedLabel` (contorno preto, ver ADR-0042) — tudo filtrado pelo mês selecionado | pronto |
| `iterador_ui/views/investments_view.py` | Lista de investimentos (chama o backend de verdade); criar/editar/remover com confirmação (ver ADR-0031); pool de linhas reaproveitado entre `refresh()` (ver ADR-0049) | pronto |
| `iterador_ui/views/budgets_view.py` | Orçamentos — metas de economia, lista com aporte mensal calculado (ver ADR-0017) | pronto |
| `iterador_ui/views/wiki_view.py` | Explicações de conceitos de finanças (CDI, Selic, receita/despesa, etc.); card CDI busca valor atual + histórico do BCB e mostra num `LineChart` (ver ADR-0021) | pronto |
| `iterador_ui/views/settings_view.py` | Configurações (versão do app; botões de importar planilha `.xlsx`, importar extrato `.csv` e exportar dados `.zip`; seção "Perfis de cor" — criar/editar/renomear/remover/aplicar, ver ADR-0025; seção "Imagem da barra lateral" — escolher/remover imagem customizada da Sidebar, ver ADR-0037/0040; seção "Interface" — escala geral (90%–150%, ver ADR-0044); seção "Categorias" — criar/remover categoria personalizada com tipo, comportamento e cor (aleatória por padrão, editável), ver ADR-0028/0030; sync/peers ainda placeholder) | pronto (versão, dados, perfis, imagem, interface, categorias) / stub (sync) |
| `iterador_ui/widgets/sidebar.py` | Menu de navegação lateral, largura travada em 180px (`pack_propagate(False)`, ver ADR-0040) — título "Iterador" via `TriangleHeading`, sempre visível; imagem customizada do usuário, se houver uma, aparece acima dele, nunca no lugar — ver ADR-0037) + botão de tema claro/escuro (quadrado, ícone sol/lua) + indicador de página ativa (`set_active`, ver ADR-0020) | pronto |
| `iterador_ui/widgets/divider.py` | Linha divisória fina reutilizável (cor vem de `theme.py`, ver ADR-0020) | pronto |
| `iterador_ui/widgets/outlined_label.py` | `OutlinedLabel` — Canvas com texto de contorno preto ao redor, largura variável (usado na coluna Categoria da lista, ver ADR-0042); sem contorno pra Investimento/Passiva e inscrito no `CTkAppearanceModeBaseClass` pra recalcular fundo/cor ao trocar tema claro/escuro (ver ADR-0047) | pronto |
| `iterador_ui/widgets/stat_card.py` | Card reutilizável rótulo+valor, `set_value()` com cor opcional | pronto |
| `iterador_ui/widgets/investment_form_dialog.py` | Diálogo modal de criação/edição de investimento (campos essenciais + "Mais opções", busca Selic, defaults de Caixinha Nubank) | pronto |
| `iterador_ui/widgets/transaction_form_dialog.py` | Diálogo modal de criar/editar lançamento (data, descrição, valor, tipo, categoria por tipo via `CategoryPicker` + investimento condicional — inclui "Nenhum (genérico)", ver ADR-0022 —, pago/pendente) | pronto |
| `iterador_ui/widgets/category_picker.py` | Grade de chips pra escolher categoria — quebra em 2ª linha e depois vira rolável, `CTkSegmentedButton` não suporta isso (ver ADR-0029) | pronto |
| `iterador_ui/widgets/color_picker_dialog.py` | Seletor de cor modernizado (CTk) — sliders R/G/B + hex + preview — substitui o `tkinter.colorchooser` nativo (ver ADR-0029) | pronto |
| `iterador_ui/widgets/image_picker_dialog.py` | `ImagePickerDialog` — diálogo de escolher imagem modernizado (CTk): "Procurar..." ainda abre o seletor nativo do sistema (navegação de arquivo real), mas com prévia estilizada da imagem escolhida antes de confirmar — usado por `SettingsView` pra trocar a imagem da Sidebar (ver ADR-0036) | pronto |
| `iterador_ui/widgets/budget_form_dialog.py` | Diálogo modal de criar/editar meta de economia (nome, valor total, meses, investimento vinculado opcional, aporte mensal calculado ao vivo, excluir) — ver ADR-0017 | pronto |
| `iterador_ui/widgets/shopping_list_dialog.py` | Diálogo "Lista de compras" — várias despesas rápidas (item+valor) viram `Transaction` Essencial/Pendente de uma vez | pronto |
| `iterador_ui/widgets/statement_review_dialog.py` | Diálogo "Importar extrato" — revisa/categoriza cada lançamento do CSV antes de confirmar (categoria não é adivinhada) — ver ADR-0024 | pronto |
| `iterador_ui/widgets/triangle_heading.py` | Fundo em mosaico triangular do título "Iterador" na Sidebar, tons de laranja amostrados do ícone, texto com contorno branco por letra, borda escura fina ao redor do retângulo — ver ADR-0025 | pronto |
| `iterador_ui/widgets/color_profile_dialog.py` | Diálogos de criar/editar (`ColorProfileDialog`, abre `ColorPickerDialog` pra cada campo de cor) e renomear (`RenameProfileDialog`) perfil de cor — ver ADR-0025/0029 | pronto |
| `iterador_ui/widgets/consumption_chart.py` | Gráfico de pizza do consumo do mês por categoria (Canvas puro), genérico pra qualquer nº de categorias — legenda em grade, cor por categoria (fixa ou paleta auxiliar por hash pras personalizadas, ver ADR-0028) | pronto |
| `iterador_ui/widgets/line_chart.py` | Gráfico de linha (Canvas puro) — `update_data()`: série única com destaque mín./máx., usado no histórico do CDI (ADR-0021); `update_series()`: multi-série (uma linha por categoria + legenda com variação %) com hover (destaque + tooltip categoria/mês/valor) e modo foco (clicar categoria na legenda prioriza ela quando linhas se sobrepõem, ver ADR-0032), usado no comparativo mensal do Início (ADR-0029/0030) | pronto |
| `iterador_ui/widgets/month_selector.py` | Faixa horizontal rolável de meses com setas ◀/▶, navegação limitada aos meses existentes, botões "+ Mês"/"Remover mês" (ver ADR-0016/0018/0019), `on_add_month` — gancho opcional avisado antes de selecionar o mês novo, pra `DashboardView` clonar transações fixadas (ver ADR-0034) | pronto |
| `iterador_ui/widgets/add_month_dialog.py` | Diálogo modal "+ Mês": campo de texto MM/AAAA, adiciona um mês vazio à tira (ver ADR-0018) | pronto |
| `iterador_ui/widgets/confirm_dialog.py` | Diálogo de confirmação genérico pra ações destrutivas (usado por "Remover mês", ver ADR-0019) | pronto |
| `iterador_ui/widgets/dialog_utils.py` | `open_singleton()` — trava pra impedir múltiplas janelas do mesmo diálogo (clique repetido no botão reaproveita a janela aberta em vez de empilhar outra); `make_modal()` — transiente/modal com `grab_set()` adiado (usado por todo diálogo do app) | pronto |
| `_build/` | Saída do CMake (`iterador_core*.so`), gitignored | gerado no build |

## `scripts/`

| Caminho | Responsabilidade | Status |
|---|---|---|
| `setup_dev_env.sh` / `.ps1` | Cria venv, instala dependências, checa `cmake` | pronto |
| `build_backend.sh` / `.ps1` | Configura e builda o `Backend/` com CMake | pronto |
| `run_ui.sh` / `.ps1` | Ativa venv e roda a UI | pronto |
| `install_desktop_launcher.sh` | Instala ícone + atalho `.desktop` no menu do KDE (Linux) | pronto |
| `build_installer_linux.sh` | Gera o instalador Linux — builda backend, congela a UI com PyInstaller, empacota num `.AppImage` (ver ADR-0035) | pronto |
| `build_installer_windows.ps1` | Gera o instalador Windows — builda backend, congela a UI com PyInstaller, compila o `Setup.exe` com Inno Setup (ver ADR-0035) | pronto |
| `packaging/iterador.spec` | Spec do PyInstaller compartilhado entre Linux/Windows (caminhos relativos a `SPECPATH`, ver ADR-0035) | pronto |
| `packaging/windows/iterador.iss` | Script do Inno Setup (Menu Iniciar, ícone opcional na área de trabalho, desinstalador) | pronto |
| `packaging/windows/icon.ico` | Ícone do `.exe`/instalador Windows, gerado uma vez a partir de `UI/assets/icon.png` (Pillow) | pronto |
| `packaging/linux/iterador.desktop` | `.desktop` embutido no AppImage (mesmo texto de `install_desktop_launcher.sh`) | pronto |
| `UI/assets/icon.png` | Logo do app (fornecido pelo usuário), usado como ícone da janela (`iconphoto`) e no atalho do menu | pronto |
| `UI/assets/icon.svg` | Mesmo logo embutido como `<image>` (data URI) — usado pelo tema de ícones do sistema (hicolor), o `.desktop` aponta pro `.png` direto | pronto |
| `UI/assets/search.png` | Ícone de lupa (fornecido pelo usuário) da barra de busca do Início — via `CTkImage`, não emoji | pronto |
| `UI/assets/sort-arrows-couple-pointing-up-and-down.png` | Ícone da alça de arrastar pra reordenar lançamentos (fornecido pelo usuário, recolorido em tempo de execução — cinza claro/escuro conforme o tema, ver ADR-0033) | pronto |
| `UI/assets/reset.png` | Ícone do botão "Resetar posições" (fornecido pelo usuário, recolorido de branco em tempo de execução, ver ADR-0033) | pronto |
| `UI/assets/Pin-on.png` / `Pin-off.png` | Ícone de fixar/desfixar transação recorrente (fornecido pelo usuário, recolorido em tempo de execução — azul/cinza, ver ADR-0034) | pronto |
