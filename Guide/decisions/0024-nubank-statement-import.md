# 0024 — Leitor de extratos Nubank (CSV) com revisão manual de categoria

Status: Aceito

## Contexto

Depois do importador da planilha (ADR-0023), o usuário quis importar também extratos bancários
do Nubank direto no Iterador. Ele forneceu um exemplo real de cada um dos dois formatos que o
Nubank exporta em CSV, confirmando que "os formatos podem variar":

- **Extrato de conta/PIX** (`NU_801721522_01SET2026_15SET2026.csv`): cabeçalho
  `Data,Valor,Identificador,Descrição`. Data `dd/mm/aaaa`; Valor já assinado igual à convenção
  do Iterador (positivo = entrada, negativo = saída); Identificador é um UUID único por
  lançamento (não persistido — o schema atual não tem campo pra isso); Descrição é texto livre
  detalhado (contraparte, CPF/CNPJ, banco).
- **Fatura de cartão de crédito** (`Nubank_2026-10-04.csv`): cabeçalho `date,title,amount` (em
  inglês, só 3 colunas — sem categoria, ao contrário do que eu tinha assumido antes de ver o
  arquivo real). Data `aaaa-mm-dd`; amount é texto com vírgula decimal (ex. `"6,00"`), às vezes
  com espaço depois do sinal (`"- 454,36"`); e o **sinal é invertido** em relação à convenção do
  Iterador — positivo na fatura é uma compra (despesa), negativo é pagamento/crédito (receita).

Diferente da planilha (que tinha a coluna Prioridade pra mapear categoria automaticamente), o
CSV do Nubank não tem nada equivalente. O usuário decidiu explicitamente que a categoria fica
**em branco por padrão, escolhida manualmente por ele** — rejeitou a alternativa de eu tentar
adivinhar por palavra-chave na descrição (mesmo tendo um padrão bem claro nos dados, tipo
"Resgate RDB"/"Aplicação RDB" que bateria certinho com Investimento/Passiva).

## Decisão

- `UI/iterador_ui/statement_import.py` — parsing puro (`parse_statement() -> 
  StatementImportResult`), detecta o formato pelo cabeçalho normalizado, sem chamada a
  `backend_bridge`. `ParsedStatementRow` não tem `category_name` (ao contrário do
  `ParsedTransaction` do importador da planilha) — só `is_income`, já resolvido a partir do
  sinal final (com a inversão aplicada pra fatura de cartão).
- `UI/iterador_ui/widgets/statement_review_dialog.py` (`StatementReviewDialog`) — diferente do
  importador da planilha, que criava tudo direto, esse abre uma tela de revisão: deduplica por
  `(data, descrição, valor)` contra o banco (mesma chave da ADR-0023) e mostra só as linhas
  novas, cada uma com um `CTkOptionMenu` de categoria começando em `"(escolher)"` (as opções são
  Despesa ou Receita conforme `is_income`) e uma caixa de marcar pra excluir a linha da leva (ex.
  "Pagamento recebido" que o usuário não queira trazer). Só as linhas categorizadas E marcadas
  viram `Transaction` ao clicar "Importar selecionados" — status sempre Pago (dinheiro do
  extrato já se moveu de verdade).
- Categoria Investimento/Passiva escolhida aqui entra sem vínculo de `Investment` (ver
  ADR-0022) — o mesmo padrão "Resgate RDB"/"Aplicação RDB" que dava pra reconhecer por
  palavra-chave também não tem como saber a qual `Investment` do Iterador se refere.
- Botão "Importar extrato (.csv)" em `SettingsView`, ao lado dos outros dois de dados.

## Consequências

- Linhas deixadas em `"(escolher)"` não geram nenhum registro — se o usuário reabrir o mesmo
  arquivo depois, elas aparecem de novo pra revisão (não ficam "perdidas" nem precisam ser
  lembradas à parte).
- Sem o Identificador (UUID) persistido, a deduplicação usa a mesma chave heurística
  (data+descrição+valor) da planilha — o texto de Descrição do extrato de conta é detalhado o
  bastante (nome da contraparte, CNPJ/CPF, banco) pra colisão ser rara na prática; se um
  identificador único vier a ser necessário, precisa de uma migration nova em
  `transactions` (schema) — não feito aqui.
- Fatura de cartão sem coluna de categoria significa que todo lançamento é tratado como uma
  compra (positivo na fatura) ou um pagamento/crédito (negativo) — não há como saber se é
  parcelado, recorrente, etc. a partir só desse CSV.
