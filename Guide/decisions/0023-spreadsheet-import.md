# 0023 — Importador da planilha Excel

Status: Aceito

## Contexto

O usuário forneceu a planilha real que usava antes do Iterador
(`Gestão contábil.xlsx`, fora do repositório) pra trazer o histórico. Lendo o arquivo de verdade
com `openpyxl` (33 abas, mai/2023–set/2026), o formato observado era bem mais inconsistente do
que `Guide/spreadsheet-reference.md` documentava a partir de amostras limitadas: o layout de
colunas mudou pelo menos 3 vezes ao longo dos anos.

## Decisão

### Formato — ver `Guide/spreadsheet-reference.md` pro detalhe completo das 3 eras

Resumo: uma aba só é importável se tiver as colunas de cabeçalho "$$$"/"Prioridade"/"Efetuado"
na primeira linha (as 2 abas mais antigas, 05-05-23 e 07-06-23, não têm — só Descrição+Valor,
sem como inferir categoria/status com confiança; **puladas**, decisão do usuário). A coluna de
Descrição é localizada dinamicamente (mais próxima à esquerda de "$$$" com texto de verdade nas
linhas de dado), porque sua posição varia entre eras. Quando não há coluna de Data por linha
(algumas abas de 2024), todas as linhas caem no dia 1 do mês/ano da aba (nome da aba é
`dd-mm-aa`) — um aviso é registrado, a importação não trava.

### Mapeamento Prioridade → categoria do Iterador

| Prioridade | Valor ≥ 0 (Receita) | Valor < 0 (Despesa) |
|---|---|---|
| 0 | Ativa | Essencial (visto só em dado inesperado/raro) |
| 1 | Ativa | Essencial |
| 2 | Ativa | Lazer |
| 3 | **Passiva** | **Investimento** |

Prioridade 3 é o mesmo "balde" de investimento nos dois sentidos (aporte e resgate) na
planilha original — o Iterador já separa isso em duas categorias por tipo (ADR-0012/0014), daí
a tabela ramificar por sinal do valor só nessa prioridade.

- `investment_id` sempre `""` (ver ADR-0022 — vínculo de investimento é opcional; a planilha não
  identifica qual `Investment` cada linha afeta).
- Efetuado 1.0 → Pago; 0.0/vazio → Pendente.
- Colunas depois de Efetuado (painel de resumo com bug, listinha "Comida") são sempre ignoradas
  — só o livro-caixa em si (Data/Descrição/Valor/Prioridade/Efetuado) é importado. A ideia da
  listinha "Comida" virou a "Lista de compras" do Iterador (reaproveitando `Transaction`
  diretamente, sem entidade nova — ver `UI/iterador_ui/widgets/shopping_list_dialog.py`).

### Onde mora

- `UI/iterador_ui/spreadsheet_import.py` — só leitura/mapeamento (`parse_workbook() ->
  ImportResult`), sem nenhuma chamada a `backend_bridge`. Retorna também `skipped_sheets` e
  `warnings` pra transparência no resumo final.
- `SettingsView` (botão "Importar planilha (.xlsx)") — escolhe o arquivo (`tkinter.filedialog`),
  roda `parse_workbook` + a criação das transações **numa thread separada** (mesmo padrão do
  fetch do CDI, ver ADR-0021/checklist — ~600 chamadas de `create_transaction` de uma vez
  travaria a janela se rodasse direto no loop principal).
- Deduplicação por `(occurred_at, description, amount_cents)` contra o que já existe no banco —
  testado rodando a importação duas vezes seguidas contra o mesmo arquivo: a segunda vez não
  cria nada novo.

## Consequências

- A chave de dedup (data+descrição+valor) pode, em teoria, colidir com um lançamento
  legitimamente diferente que por coincidência tenha os três iguais a outro (aconteceu 5 vezes
  na planilha real do usuário, dentro do próprio arquivo) — aceito como troca razoável por não
  ter nenhum identificador melhor vindo da planilha.
- Linhas com valor preenchido mas sem descrição (a planilha tem algumas, ex. um resgate sem
  texto) são ignoradas com aviso — não dá pra criar um `Transaction` sem descrição.
- Não há tela de "prévia antes de confirmar" — o botão já importa direto, mostrando um resumo
  (quantos criados/pulados/abas ignoradas/avisos) depois. Decisão do usuário: ficar em
  Configurações como uma ação direta, não um assistente com passos.
- Só suporta `.xlsx` por enquanto (não `.csv`) — não foi pedido formato adicional.
