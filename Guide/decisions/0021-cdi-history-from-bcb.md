# 0021 — CDI atual + histórico na Wiki, direto do Banco Central

Status: Aceito

## Contexto

Depois de discutir quais indicadores externos valeriam a pena o app acompanhar (além da Selic,
já buscada desde o ADR-0008), o usuário pediu concretamente pelo CDI: encontrar uma fonte
confiável pra buscar o valor online, e mostrar numa "seção do CDI" tanto o valor atual quanto um
gráfico com a linha do tempo dos altos/baixos.

CDI (Certificado de Depósito Interbancário) é a taxa mais citada nos investimentos pós-fixados
do usuário (Caixinha Nubank inclusive) — mais relevante no dia a dia do que a própria Selic, já
que "% do CDI" é como a rentabilidade é anunciada, apesar de o app até agora só buscar Selic.

## Decisão

### Fonte

Banco Central do Brasil, mesma API SGS já usada pra Selic (`api.bcb.gov.br/dados/serie/
bcdata.sgs.<código>/dados`) — é a fonte primária/oficial no Brasil (o CDI em si é calculado e
divulgado pela B3, mas o BCB replica a série publicamente, sem exigir cadastro/chave de API,
diferente do portal da B3). Duas séries usadas:

- **4389** ("Taxa de juros - CDI anualizada base 252", % a.a.) — pro valor atual e pro histórico.
  Escolhida em vez da série 12 (CDI diário, ex. "0,0517% ao dia" — correta mas ilegível pra
  humano) ou da 4391 (CDI mensal) porque "% a.a." é o formato em que o CDI é comumente divulgado
  e comparado (mesmo formato que a Selic já usa no app, ver ADR-0008) — ex. "CDI a 13,90% a.a.".
- Confirmado por teste direto na API (não documentado claramente nos datasets do
  `dadosabertos.bcb.gov.br`, mas confirmado batendo com a relação conhecida
  **CDI ≈ Meta Selic − 0,10 p.p.**: 4389 retornou 13,90% no mesmo dia em que a Meta Selic
  (série 432) estava em 14,00%).

### Busca (`UI/iterador_ui/market_data.py`)

- `fetch_current_cdi_rate()` — mesmo padrão de `fetch_current_selic_rate()`: busca
  `.../ultimos/1`, retorna `CdiRate(percent_per_year, reference_date)` ou `None` em qualquer
  falha (offline tolerante, nunca lança exceção).
- `fetch_cdi_history(years=3)` — busca com `dataInicial`/`dataFinal` (não `ultimos/N`, pra pegar
  um intervalo de calendário exato) cobrindo os últimos `years` anos; retorna lista de
  `(data "dd/mm/aaaa", valor)` em ordem cronológica, ou `None` em falha. 3 anos de dados diários
  são ~750 pontos — testado contra a API real, retorna rápido (a série é um "degrau": só muda
  de valor quando o Copom se reúne, então o JSON é pequeno mesmo com 750 entradas).

### `LineChart` (novo widget, `UI/iterador_ui/widgets/line_chart.py`)

- `tkinter.Canvas` puro, mesmo estilo do `ConsumptionChart` (fundo Carbon Black fixo,
  independente do tema claro/escuro). `update_data(points: list[tuple[str, float]])` desenha a
  linha inteira, destaca o ponto de valor mínimo (vermelho, `theme.VALUE_EXPENSE`) e máximo
  (verde, `theme.VALUE_INCOME`) com um círculo + rótulo do valor, e mostra a primeira/última data
  nos cantos inferiores. Genérico o bastante pra reusar com qualquer outra série temporal futura
  (ex. IPCA, se for pedido) — não é específico de CDI.

### Onde entrou na UI

- `WikiView`, especificamente no card "CDI" (que já existia, só com texto explicativo) — o
  card ganhou um rótulo com o valor atual, o `LineChart` com o histórico, e um botão "Atualizar
  CDI (BCB)". A busca acontece **automaticamente ao abrir a aba Wiki** (não só no clique do
  botão) — diferente do padrão do botão de Selic em `InvestmentFormDialog` (que só busca no
  clique), porque aqui o pedido foi "mostre o valor", não "deixe disponível pra buscar". O botão
  continua existindo pra atualizar sem sair da aba.
- Chamada síncrona (mesma filosofia de todo o resto do app): trava a UI por até ~15s no pior
  caso (timeout de 5s pro valor atual + 10s pro histórico, se estiver offline) toda vez que a
  Wiki é aberta. Aceitável no caso comum (API responde rápido, testado), e consistente com como
  o botão de Selic já funciona — não foi introduzida nenhuma complexidade de thread/callback
  assíncrono pra evitar isso.

## Consequências

- `fetch_cdi_history` sempre busca os últimos 3 anos fixos — não há seletor de intervalo (ex.
  "1 ano"/"5 anos") na UI. Fácil de adicionar depois se for pedido (o parâmetro `years` já
  existe na função).
- Nenhuma persistência local do histórico buscado — cada abertura da Wiki refaz as duas chamadas
  de rede. Não é cacheado em disco nem no banco SQLite (não faz sentido guardar dado de mercado
  externo junto com dado financeiro do usuário).
- `LineChart` não tem eixo Y numerado nem grade — só a linha, os dois pontos extremos rotulados,
  e as datas de início/fim. Suficiente pro pedido ("mostrar os altos e baixos"), mas é uma
  visualização bem simples comparada a uma lib de gráficos de verdade — deliberado, pra não
  introduzir uma dependência nova (matplotlib) só por isso, mesmo raciocínio do
  `ConsumptionChart` original.
