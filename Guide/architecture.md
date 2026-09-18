# Arquitetura

## Visão geral

```
┌─────────────────────────────┐        LAN / Tailscale        ┌─────────────────────────────┐
│  Dispositivo A (Linux/Win)   │◄──────────────────────────────►│  Dispositivo B (Linux/Win)   │
│                               │        (protocolo de sync)     │                               │
│  ┌─────────────────────────┐ │                                 │ ┌─────────────────────────┐ │
│  │ UI/  (CustomTkinter)     │ │                                 │ │ UI/  (CustomTkinter)     │ │
│  │  views/ + widgets/       │ │                                 │ │  views/ + widgets/       │ │
│  └────────────┬─────────────┘ │                                 │ └────────────┬─────────────┘ │
│               │ backend_bridge.py (único ponto que importa      │              │               │
│               │ iterador_core)                                  │              │               │
│  ┌────────────▼─────────────┐ │                                 │ ┌────────────▼─────────────┐ │
│  │ Backend/ (C++, via        │ │                                 │ │ Backend/ (C++)            │ │
│  │ pybind11 — processo único)│ │                                 │ │                           │ │
│  │  app/Application (fachada)│ │                                 │ │  app/Application          │ │
│  │  storage/ (SQLite local)  │ │                                 │ │  storage/ (SQLite local)  │ │
│  │  sync/ (thread própria) ──┼─┼─────────────────────────────────┼─┼► sync/                    │ │
│  └───────────────────────────┘ │                                 │ └───────────────────────────┘ │
└─────────────────────────────┘                                 └─────────────────────────────┘

Android (App/, fase futura): app nativo Kotlin que eventualmente falará o mesmo protocolo de sync.
```

Cada dispositivo roda um processo único: a UI CustomTkinter com o backend C++ carregado dentro
dela como módulo Python (via pybind11) — não há processo servidor separado para uso local. O que
atravessa a rede é só o protocolo de sincronização entre as instâncias do `SyncEngine` de cada
dispositivo.

## Modelo de dados: carteira única (não existe "Conta")

**Não há conceito de múltiplas contas no Iterador.** O usuário tem uma carteira única e
implícita — não existe tela de "criar conta" nem tipos de conta. O valor do usuário fica em
dois lugares (ver [ADR-0007](decisions/0007-remove-account-add-investment.md)):

- **Dinheiro** — saldo líquido. Ainda não modelado como entidade própria (ver Roadmap).
- **Investimentos** (`core::Investment`) — cada um nomeado e tipado livremente pelo usuário
  (ex. "Tesouro Selic" / "Renda fixa"), com rentabilidade, taxas e um percentual relativo à
  Selic/CDI. É a fatia de referência implementada de ponta a ponta (era `Account` antes da
  correção de escopo).

## Camadas do Backend (`Backend/src/`)

```
core/        modelos de domínio puros (Money, Id, Timestamp, Investment, Category, Transaction, Budget)
   ↑ usado por
storage/     Database (SQLite) + um Repository por entidade + OperationLog
   ↑ usado por
sync/        descoberta de peers + protocolo + HybridLogicalClock + SyncEngine (thread própria)
   ↑ usado por
app/         Application — fachada única, combina storage + sync
   ↑ usado por
bindings/    pybind11 — expõe só Application (e os tipos de core/ que ela retorna) ao Python
```

A UI **nunca** importa `storage/` ou `sync/` diretamente — só fala com `Application` através de
`UI/iterador_ui/backend_bridge.py`. Isso mantém a fronteira C++↔Python pequena e estável mesmo
que o interior do backend mude.

**Migrations de schema:** `Backend/src/storage/migrations/000N_*.sql`, embutidas no binário via
CMake (`EmbeddedMigrations.hpp.in`) e aplicadas em `Database::runMigrations()` com um bloco
`if (currentUserVersion() < N)` por migration. **Uma migration já embutida em release nunca é
editada** — o usuário já tem dados reais migrados (ver CLAUDE.md e ADR-0012, onde a migration
0002 foi testada simulando um banco na versão anterior antes de considerar pronta).

## Modelo de sincronização P2P

- Sem servidor central. Cada dispositivo tem seu próprio SQLite e funciona 100% offline.
- Toda mutação nos repositórios grava uma entrada em `operation_log` (event sourcing) — o `sync/`
  nunca precisa saber de regras de negócio, só replica e aplica entradas de log.
- Ordenação e resolução de conflito usam um **Hybrid Logical Clock** (relógio de parede + contador
  lógico + id do dispositivo), não um vector clock completo — decisão registrada em
  [`decisions/0006-hybrid-logical-clock-lww-conflict-resolution.md`](decisions/0006-hybrid-logical-clock-lww-conflict-resolution.md).
  Conflito = HLC maior vence (last-write-wins).
- Descoberta de peers:
  - **LAN:** broadcast/multicast UDP numa porta dedicada, cada dispositivo anuncia
    `{device_id, device_name, app_version, sync_port}` periodicamente; entradas expiram sem sinal.
  - **Tailscale:** lista local `peers.json` (hostnames/IPs conhecidos), cadastrada manualmente
    nesta fase; automação via `tailscale status --json` fica para depois.
- `SyncEngine` roda em thread própria dentro do processo. **Regra importante:** essa thread nunca
  chama de volta para dentro do Tk/CustomTkinter — a UI consulta `SyncStatus` por polling
  (ex. `app.after(...)`), nunca recebe callback direto da thread de sync.

## Identidade visual (UI)

Paleta de cores do Iterador, definida em [`UI/iterador_ui/theme.py`](../UI/iterador_ui/theme.py)
como um sistema de **perfis de cor** persistidos e editáveis pelo usuário (ver
[ADR-0020](decisions/0020-color-profile-system.md) pro conceito original e
[ADR-0025](decisions/0025-color-profile-management.md) pro CRUD de verdade — criar/editar/
renomear/remover em Configurações, `UI/iterador_ui/color_profiles.py`). Dois tipos de papel:

- **Fixos** (`theme._fixed_roles()`) — iguais em qualquer perfil, não editáveis pelo usuário:

  | Nome | Uso |
  |---|---|
  | Brick Ember | **Cor de destaque principal** do app (ex. despesas, botões primários) |
  | Indigo | Cor de destaque secundária (ex. receitas, elementos de navegação) |
  | Carbon Black | Texto principal e fundos escuros |
  | Deep Saffron | Botão de status "A pagar" na lista de lançamentos (laranja) |
  | Sunflower Gold | Acentos (borda do painel de mês/"Fim do mês" no Início, botão de tema no escuro) — hoje um laranja (`#F8A000`) amostrado do ícone do app, não mais o amarelo original |
  | Electric Blue | Separadores estruturais (cabeçalhos, barra de colunas da lista) e borda dos botões de contorno (`theme.outline_button_style()`) |

  Valores monetários (verde/vermelho), cor por categoria e badge Pago/A pagar também são fixos —
  nenhum perfil muda esses.
- **Estruturais** (fundo do app/painel/card, texto estático, bordas/separadores) — variam por
  perfil. O perfil `Prizmo_V1` (o visual de sempre, salvo tal como estava) guarda esses papéis
  detalhados, um por um; um perfil novo criado pelo usuário simplifica tudo isso em só 4 cores
  (Primária/Secundária/Terciária/Texto estático — ver ADR-0025).

Separadores finos (`UI/iterador_ui/widgets/divider.py`) marcam a estrutura da tela sem precisar
de borda em cada widget: `BORDER_NEUTRAL` entre os itens da sidebar, `NAV_INDICATOR_ACTIVE`
(vermelho, fixo) na página atualmente selecionada, `BORDER_ACCENT` nas divisões estruturais do
Início, `ROW_SEPARATOR` entre cada lançamento da lista — ver ADR-0020 (estruturais, variam com o
perfil ativo).

O logo/título "Iterador" na sidebar não usa mais fundo sólido — é uma textura de mosaico
triangular (`UI/iterador_ui/widgets/triangle_heading.py`, `TriangleHeading`) com tons de laranja
amostrados de verdade do ícone do app (análise de pixel de `UI/assets/icon.png`, não escolhidos
a olho), texto em Carbon Black por cima — ver ADR-0025. O ícone do app em si (usado no menu do
KDE e na janela via `iconphoto`) é o logo fornecido pelo usuário, desenho diferente do
título/sidebar; `icon.svg` embute o mesmo PNG como fallback pro tema de ícones do sistema.

**Tema claro/escuro:** todo papel de cor "neutro" (fundo, texto de corpo) é uma tupla
`(claro, escuro)` — CustomTkinter troca sozinho quando `ctk.set_appearance_mode()` muda, sem
precisar recolorir widget por widget (perfis "simple" usam a mesma cor nos dois temas de
propósito, ver ADR-0025). O botão de tema fica no rodapé da sidebar
(`UI/iterador_ui/widgets/sidebar.py`, quadrado, com ícone de sol/lua minguante — era um
`CTkSwitch` antes), e `IteradorApp._on_toggle_theme` (`UI/iterador_ui/app.py`) é quem chama
`ctk.set_appearance_mode(...)`, persistindo a escolha em `~/.iterador/preferences.json`
(`UI/iterador_ui/preferences.py`) — o app já abre no último modo escolhido, não sempre em
"dark". O botão em si usa cores invertidas de propósito (`theme.THEME_SWITCH_DARK_COLOR` =
Sunflower Gold/laranja no modo escuro, `THEME_SWITCH_LIGHT_COLOR` = cinza no modo claro — ver
ADR-0013). A sidebar inteira usa `BG_PANEL_BLUE` (papel estrutural) como fundo próprio, sem
frame aninhado por baixo. Trocar de **perfil** (não de tema) em runtime exige reconstruir a UI
(`IteradorApp.rebuild_ui()`, ver ADR-0025) — mudar o valor de um papel estrutural não recolore
sozinho um widget já construído, diferente de trocar claro/escuro.

## Roadmap — o que ainda não está implementado

- `Budget` agora é meta de economia (CRUD completo, ver
  [ADR-0017](decisions/0017-savings-goal-budgets.md)), não limite de gasto por categoria — não há
  mais nenhuma entidade em stub além de `sync/`. `Category`/`Transaction` já implementados de
  ponta a ponta (ver [ADR-0010](decisions/0010-dashboard-hosts-transactions.md)/
  [ADR-0012](decisions/0012-fixed-categories-and-investment-link.md)/
  [ADR-0014](decisions/0014-category-rename-colors-and-sign-fix.md)) com 5 categorias fixas por
  Tipo — Despesa: Essencial/Lazer/Investimento; Receita: Ativa/Passiva — mais categorias
  personalizadas criáveis em Configurações (`custom_categories.py`, sem mudança nenhuma em C++
  — o backend já era genérico, ver [ADR-0028](decisions/0028-custom-categories.md)).
- **Dinheiro (saldo líquido)** ainda não tem representação própria no modelo — "Fim do mês" no
  Início (`DashboardView`) já filtra por mês selecionado (ver
  [ADR-0016](decisions/0016-monthly-transaction-navigation.md)), mas ainda não separa de
  Investimentos.
- Meta de economia (`Budget`) não tem nenhuma automação de "concluída" — não compara
  `investment.current_value` com `budget.target_value` nem marca visualmente quando a meta é
  atingida (ver ADR-0017).
- `TransactionType::Transfer` (aporte/resgate ligado a um `Investment`) já tem o campo
  `investmentId` e o ajuste automático de valor funciona (ver ADR-0012) — mas hoje isso acontece
  em qualquer `TransactionType` (a categoria "Investimento" é quem decide, não o tipo Transfer
  em si), e o ajuste ignora status pago/pendente (afeta o investimento mesmo "a pagar").
- Modelo de `Transaction` além de status pago/pendente e data (ver ADR-0011): data de
  vencimento separada da data efetiva, parcelamento, recorrência. Depende de detalhes de fluxo
  que o usuário ainda vai passar.
- Formato exato de `yieldRate`/`feesRate`/`selicPercentage` em `Investment` (ao ano? ao mês? "%
  do CDI"?) — primeiro rascunho, a confirmar com o usuário (ver ADR-0007).
- **Cálculo de rentabilidade efetiva**: já buscamos a Selic atual online
  ([ADR-0008](decisions/0008-fetch-selic-rate-from-bcb.md)), mas ainda não usamos isso para
  calcular/mostrar o rendimento estimado de cada investimento (`selic_percentage × Selic
  atual`). Faltam também variáveis descobertas na pesquisa que o modelo ainda não tem: tipo de
  indexador (pós-fixado/prefixado/IPCA+), prazo em dias úteis, e tributação (IR regressivo sobre
  renda fixa: 22,5%/20%/17,5%/15% conforme o prazo).
- **Importação de planilhas Excel**: implementada de ponta a ponta
  (`UI/iterador_ui/spreadsheet_import.py` + botão em Configurações, ver
  [ADR-0023](decisions/0023-spreadsheet-import.md)) — a estrutura real da planilha do usuário
  está mapeada em [`spreadsheet-reference.md`](spreadsheet-reference.md). O painel de alocação
  financeira completo (percentuais da planilha) continua pendente — ver item logo abaixo.
- Painel de alocação financeira completo (percentuais tipo "Investimento 57,92%" da planilha) —
  o gráfico de consumo por categoria já existe, mas não replica o painel numérico inteiro;
  aguardando o usuário confirmar a fórmula correta (a planilha original tem um bug conhecido, ver
  [ADR-0015](decisions/0015-financial-allocation-panel-review.md)).
- Regras de negócio: transações recorrentes (inclusive pré-popular um mês novo com lançamentos
  recorrentes).
- Sync P2P funcionando de ponta a ponta: descoberta UDP real, handshake TCP, troca e aplicação de
  `operation_log`, resolução de conflito por HLC. Hoje as classes de `sync/` são só assinaturas.
- Autenticação/criptografia do tráfego de sync (fase 1 assume LAN/Tailscale como perímetro
  confiável; isso precisa virar seu próprio ADR quando for endereçado).
- Empacotamento/instaladores, assinatura de código, auto-update, CI/CD.
- App Android (`App/`) falando o mesmo protocolo de sync — hoje é só o template padrão do Android
  Studio, sem integração nenhuma com o Backend.
