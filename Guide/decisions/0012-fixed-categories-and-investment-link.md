# 0012 — Categorias fixas + transação ligada a um investimento

Status: Aceito

## Contexto

O usuário pediu três coisas interligadas:

1. O gráfico de consumo do Início deveria agrupar por **categoria**, não por transação
   individual (antes agrupava por `description`, que era só o texto livre digitado).
2. Categoria vira um seletor fixo (botão listável) em cada transação: **Necessário**, **Lazer**,
   **Investimento** — substituindo o fluxo anterior de achar/criar categoria pelo texto da
   descrição (ADR-0010).
3. Quando a categoria escolhida é "Investimento", um segundo seletor aparece com os
   investimentos existentes — a transação passa a **influenciar o valor** do investimento
   escolhido.

Isso resolve de vez um ponto em aberto desde o ADR-0007 (como `Transaction` referencia qual
`Investment` num movimento) e também aproxima o app do sistema de baldes por prioridade da
planilha original do usuário (Essencial/Desejável/Investimento — ver
`spreadsheet-reference.md`), sem precisar copiar a fórmula com bug do painel de alocação.

## Decisão

- **Migration 0002** (`0002_link_transaction_investment.sql`): `ALTER TABLE transactions ADD
  COLUMN investment_id TEXT REFERENCES investments(id)`, nullable. Testado simulando um banco na
  versão 1 (schema antigo, com dados) antes de considerar pronto — confirma que dados existentes
  do usuário não são afetados, só ganham a coluna nova vazia.
- `core::Transaction` ganhou `investmentId` (opcional, `""` = nenhum) e `categoryName` (só
  leitura — populado via `JOIN categories` em `TransactionRepository`, não é uma fonte de
  verdade separada).
- `Application::createTransaction`/`updateTransaction` recebem `categoryName` (uma das 3 fixas,
  vinda da UI) em vez de usar a descrição, e `investmentId`. Categoria continua sendo
  achada/criada via `CategoryRepository::findOrCreateByName` — só muda o que é passado como nome.
- **Regra de influência no investimento** (`Application::adjustInvestmentValue`): o delta
  aplicado ao investimento é **o negativo do valor da transação**. Uma despesa (valor negativo,
  ex. um aporte) soma no investimento; uma receita (valor positivo, ex. um resgate) subtrai.
  Isso é aplicado em `create`, revertido+reaplicado em `update` (busca o estado anterior via
  `findById` antes de sobrescrever), e revertido em `delete` — testado com uma sequência
  completa: criar aporte → editar valor → deletar → confere que o investimento volta exatamente
  ao valor original em cada passo.
- `ConsumptionChart` (Início) agrupa despesas por `category_name` em vez de `description` —
  inclui a categoria "Investimento" como fatia (igual ao gráfico "Alocações Financeiras" da
  planilha original, que também tinha investimento como um dos três blocos).
- `TransactionFormDialog` ganhou um `CTkSegmentedButton` de Categoria e um `CTkOptionMenu`
  condicional de Investimento (só aparece quando a categoria é "Investimento"), populado via
  `backend_bridge.list_investments()`.

## Consequências

- O ajuste no investimento acontece **na criação/edição/remoção**, independente do status
  Pago/Pendente da transação — uma transação "a pagar" ligada a um investimento já mexe no valor
  dele, o que não é totalmente realista (o aporte ainda não aconteceu de fato). Simplificação
  deliberada; revisitar se isso incomodar no uso real (ver Roadmap).
- `TransactionRepository::create`/`findById`/`listAll` agora fazem `JOIN` com `categories` — leve
  overhead, irrelevante no volume atual de dados.
- Se um investimento ligado a transações for removido no futuro (não há UI de remover
  investimento ainda), `adjustInvestmentValue` simplesmente não encontra o investimento e não
  faz nada — as transações antigas continuam com um `investment_id` "órfão". Não tratado ainda.
- "Necessário"/"Lazer" não têm nenhum comportamento especial além de aparecerem no gráfico —
  diferente de "Investimento", que é a única categoria com efeito colateral. Se o usuário quiser
  mais categorias no futuro, isso precisa virar uma lista configurável em vez de fixa no código.
