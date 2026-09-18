# 0008 — Buscar a taxa Selic online via API do Banco Central

Status: Aceito

## Contexto

O usuário pediu que o programa seja capaz de buscar online variáveis usadas no cálculo de
rentabilidade de investimentos, começando pela taxa Selic — em vez de o usuário precisar
digitar/atualizar esse número manualmente.

Pesquisei como calcular rentabilidade de renda fixa brasileira e a API pública do Banco Central
antes de implementar (ver fontes abaixo). Resumo do que aprendi:

- Investimentos pós-fixados (ex. CDB, Tesouro Selic) rendem como percentual do CDI/Selic (ex.
  "110% do CDI") — é exatamente o campo `Investment.selicPercentage` que já existia no modelo.
- A fórmula padrão é `Montante Final = Valor Inicial × (1 + taxa_anual)^(dias_uteis/252) × (%
  contratado)` — usa 252 (dias úteis/ano no mercado financeiro brasileiro), não 365.
- Variáveis que o usuário ainda não tinha mencionado e que aparecem em qualquer cálculo real:
  tipo de indexador (pós-fixado/CDI, prefixado, ou híbrido IPCA+), prazo em dias úteis, e
  **tributação** (Imposto de Renda regressivo sobre renda fixa: 22,5% até 180 dias, 20% de
  181–360, 17,5% de 361–720, 15% acima de 720 dias) — nenhuma dessas está modelada ainda.
- A API do Banco Central (SGS — Sistema Gerenciador de Séries Temporais) expõe várias séries
  relacionadas à Selic, cada uma com um significado diferente:
  - Série 11: Selic diária efetiva (ex. `0.051660`, ou seja ~0,05% ao dia).
  - Série 1178: Selic anualizada, base 252 (ex. `13.90`).
  - Série 432: **Meta Selic definida pelo Copom** (ex. `14.00`) — é o número que aparece nas
    manchetes ("Copom mantém a Selic em 14,00%"), o que as pessoas normalmente chamam de "a
    Selic".

## Decisão

Buscar a **série 432** (Meta Selic) via
`https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json` — é o valor que
corresponde ao que o usuário reconhece como "a taxa Selic atual".

Implementado em `UI/iterador_ui/market_data.py` (`fetch_current_selic_rate()`), chamado por um
botão "Buscar taxa Selic atual (BCB)" no formulário de investimento
(`widgets/investment_form_dialog.py`) — busca síncrona (a API responde rápido, timeout de 5s),
preenche um label informativo. **Não** autopreenche o campo "% da Selic/CDI" automaticamente,
porque são números diferentes: a Selic atual é uma taxa de mercado (ex. 14,00% a.a.), enquanto
"% da Selic/CDI" é um termo contratual do investimento específico (ex. "rende 110% da Selic").

## Consequências

- É a única chamada de rede da UI para fora do protocolo de sync (ver
  [ADR-0003](0003-p2p-sync-no-central-server.md)) — fica isolada em `market_data.py`, igual
  `backend_bridge.py` isola o `iterador_core`.
- Tolerante a falha por design: qualquer erro de rede retorna `None` em vez de lançar exceção —
  o app precisa continuar funcionando 100% offline (mesma filosofia do resto do projeto).
- **Não implementado ainda** (ver Guide/architecture.md > Roadmap): usar a Selic buscada para
  calcular e mostrar a rentabilidade efetiva estimada de cada investimento
  (`selic_percentage × Selic_atual`), e modelar tributação (IR regressivo) e tipo de indexador
  (pós-fixado/prefixado/IPCA+) — meros aumentos do escopo atual de `Investment`, aguardando
  confirmação do usuário sobre até onde ele quer que o cálculo vá.

## Fontes consultadas

- [Como calcular CDI e aproveitar a rentabilidade hoje?](https://blog.inter.co/como-calcular-cdi/)
- [CDI: o que é, como funciona e como calcular seus rendimentos](https://naosoueconomista.com.br/educacao-financeira/cdi-o-que-e-como-funciona-e-como-calcular-seus-rendimentos/)
- [Portal de Dados Abertos do Banco Central — Taxa de juros Selic (série 11)](https://dadosabertos.bcb.gov.br/dataset/11-taxa-de-juros---selic/resource/b73edc07-bbac-430c-a2cb-b1639e605fa8)
- [Portal de Dados Abertos do Banco Central — Selic anualizada base 252 (série 1178)](https://dadosabertos.bcb.gov.br/dataset/1178-taxa-de-juros---selic-anualizada-base-252/resource/e7fe6edb-d6c3-49b1-a7ef-6e0e98b63270)
