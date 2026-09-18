# 0014 — Categorias por tipo, cores fixas, correção de sinal, lista rolável

Status: Aceito

## Contexto

Ajustes do usuário sobre o que foi feito no ADR-0012:

1. "Necessário" devia se chamar **"Essencial"**.
2. Categorias ganham cor fixa: Essencial vermelho, Lazer verde, Investimento roxo.
3. **As 3 categorias (Essencial/Lazer/Investimento) só valem para Despesa.** Receita usa outro
   conjunto: **Ativa** e **Passiva** — Passiva roxa, Ativa verde.
4. A lista de lançamentos ficava escondida abaixo do limite da janela com muitos itens, sem
   como rolar.
5. **Correção crítica de sinal**: o ADR-0012 tinha implementado a lógica ao contrário. O usuário
   esclareceu: uma **despesa categoria Investimento é um saque — subtrai** do investimento
   selecionado (não soma, como eu tinha feito).

## Decisão

- Categorias viram dois conjuntos fixos em `backend_bridge.py`:
  `EXPENSE_CATEGORY_NAMES = ["Essencial", "Lazer", "Investimento"]` e
  `INCOME_CATEGORY_NAMES = ["Ativa", "Passiva"]`. `TransactionFormDialog` troca as opções do
  `CTkSegmentedButton` de Categoria (via `.configure(values=...)`) toda vez que o Tipo
  (Despesa/Receita) muda, resetando pra primeira opção válida se a categoria atual não existir
  mais no novo conjunto.
- `INVESTMENT_LINKED_CATEGORIES = {"Investimento", "Passiva"}` — as duas categorias "roxas" são
  as duas ligadas a investimento (não por coincidência de cor: Investimento = saque, Passiva =
  aporte/rendimento — ver correção de sinal abaixo). O seletor de investimento na UI aparece pra
  qualquer uma das duas.
- `theme.CATEGORY_COLORS` (dict nome→cor) + `theme.category_color(name)` (sempre retorna cor
  resolvida, não-tupla — funciona tanto em `CTkLabel` quanto no `tkinter.Canvas` puro do
  `ConsumptionChart`). Essencial=vermelho puro, Lazer=verde claro, Investimento=roxo (Indigo),
  Ativa=verde claro, Passiva=roxo. O gráfico de consumo agora usa essas mesmas cores fixas por
  fatia em vez de cores cíclicas — funciona como legenda consistente com a lista.
- **`DashboardView._list_frame` virou `CTkScrollableFrame`** (era `CTkFrame`) — mesma API de
  `.grid()` para as linhas, ganha rolagem de graça.
- **Correção de sinal em `Application::adjustInvestmentValue`**: o delta aplicado ao
  investimento agora é `amountCents` diretamente (sem inverter o sinal). Como despesa já é
  negativa: despesa categoria Investimento (saque) **subtrai**; receita categoria Passiva
  (aporte/rendimento) **soma**. `update`/`delete` foram ajustados simetricamente (reversão
  também sem inverter). Testado a sequência completa: criar saque → editar valor do saque →
  deletar, conferindo o valor do investimento em cada passo.

## Consequências

- Dados reais que o usuário já tinha criado como categoria "Necessário" continuam com esse nome
  no banco — a renomeação é só no código (`findOrCreateByName` agora cria/acha "Essencial" para
  transações novas), não uma migração retroativa dos dados existentes. Editar uma transação
  antiga recategoriza ela pra "Essencial" (ou outra escolhida).
- Transações criadas **antes** desta correção com categoria Investimento/Passiva ligadas a um
  investimento (durante o período em que o sinal estava invertido) deixaram o valor do
  investimento errado (na direção oposta à pretendida). Não corrigido retroativamente — não
  havia nenhuma transação real do tipo no banco do usuário até este ponto, só nos meus próprios
  testes isolados em `/tmp`.
- "Essencial"/"Lazer"/"Ativa" continuam sem efeito colateral (só aparecem no gráfico/lista) —
  únicas categorias com efeito real no investimento são Investimento e Passiva.
