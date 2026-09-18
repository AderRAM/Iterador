# 0027 — Views reaproveitadas entre trocas de aba (correção de performance)

Status: Aceito

## Contexto

O usuário relatou "delay considerável" ao sair e voltar pro Início. `IteradorApp.show_view()`
(`UI/iterador_ui/app.py`) destruía a view atual e construía a nova do zero a cada troca de aba,
inclusive voltando pra uma aba já visitada antes. Pra Início (`DashboardView`) isso custava o
mesmo que o primeiro carregamento sempre — cronometrado contra uma cópia do banco real: **~2,5s**
(a maior parte é construir a lista de lançamentos + gráfico + cards do zero, ver ADR-0026). Como
o pool de widgets da ADR-0026 vive na instância da `DashboardView`, destruir a view a cada troca
de aba jogava o pool fora também — voltar pro Início nunca se beneficiava do pool "quente",
sempre pagava o custo de construção completo de novo.

## Decisão

`IteradorApp` mantém um cache `self._views: dict[str, view]` — cada view é construída **uma vez**
na primeira visita e reaproveitada nas trocas seguintes (`show_view()` usa `pack_forget()`/
`pack()` em vez de `destroy()`/recriar). Ao voltar pra uma view já em cache que expõe `refresh()`
(`DashboardView`, `BudgetsView`, `InvestmentsView`), esse método é chamado pra recarregar os dados
do backend sem reconstruir os widgets — mantém os dados atuais (ex. um lançamento criado numa
aba deve aparecer se ele afetasse outra) sem pagar o custo de reconstrução.

`rebuild_ui()` (troca de perfil de cor, ver ADR-0025) precisa destruir e limpar o cache inteiro
(`self._views = {}`), não só a view atual — as views escondidas em cache ficariam com as cores
antigas presas se não fossem descartadas também.

## Verificação

Contra a mesma cópia do banco real (ADR-0026): alternar Início ↔ outra aba repetidamente.

| Cenário | Antes | Depois |
|---|---|---|
| 1ª visita ao Início (parte do startup do app) | ~2500 ms | ~2500 ms (inevitável, é a 1ª vez) |
| Voltar ao Início (2ª visita em diante) | ~2500 ms (igual à 1ª vez, sempre) | **~100 ms**, estável em 5 repetições seguidas |

## Consequências

- Views ficam vivas (não destruídas) enquanto o app roda, exceto durante `rebuild_ui()` — leve
  aumento de memória residente (poucos widgets Tk por view), aceitável frente ao ganho.
- `BudgetsView`/`InvestmentsView` ainda destroem/recriam a lista interna deles a cada `refresh()`
  (não têm pool como a ADR-0026) — fora do escopo deste ADR, que só resolve o relato específico
  de lentidão no Início.
