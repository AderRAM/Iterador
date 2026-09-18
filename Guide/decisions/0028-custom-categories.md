# 0028 — Categorias personalizadas + gráfico de consumo adaptável

Status: Aceito

## Contexto

Até aqui só existiam 5 categorias, hardcoded na UI (`Essencial`/`Lazer`/`Investimento` para
Despesa, `Ativa`/`Passiva` para Receita — ver ADR-0014). O usuário pediu uma tela em
Configurações pra criar categorias novas, escolhendo se cada uma se comporta "como um tipo de
investimento" (mostra o seletor de investimento e ajusta o valor dele, como Investimento/Passiva
hoje) ou "como um gasto/receita comum" (só categoriza, como Essencial/Lazer/Ativa) — e pediu que
o gráfico "Consumo do mês" aguente mais categorias sem quebrar o layout. Isso resolve o item já
registrado em `Guide/checklist.md`: *"Tela pra gerenciar categorias além das 3 fixas... hoje é
código fixo, não configurável"*.

## Decisão

**Tudo resolvido no lado Python/UI, sem mudar o C++.** Investigação confirmou que o backend já é
genérico: `CategoryRepository::findOrCreateByName`
(`Backend/src/storage/CategoryRepository.cpp`) já acha-ou-cria uma linha na tabela `categories`
pra **qualquer** nome passado por `create_transaction`/`update_transaction` — a lista fixa de "só
essas 5 existem" sempre foi só uma convenção da UI, não uma restrição do banco. Da mesma forma, a
ligação Investimento/Passiva → `Application::adjustInvestmentValue` só olha se `investmentId`
está vazio, nunca o nome da categoria — quem decide mostrar o seletor de investimento é
inteiramente `transaction_form_dialog.py`, comparando contra
`backend_bridge.INVESTMENT_LINKED_CATEGORIES`.

- **`UI/iterador_ui/custom_categories.py`** (novo) — persistência em
  `~/.iterador/custom_categories.json` (nunca o banco), mesmo padrão de `color_profiles.py`/
  `preferences.py`. Cada categoria personalizada guarda `name`, `type` (Despesa/Receita) e
  `investment_linked` (bool). `remove_custom_category()` só tira da lista de opções — nunca mexe
  em lançamentos já gravados (mesmo princípio da categoria órfã "Necessário").
- **`backend_bridge.py`** — `EXPENSE_CATEGORY_NAMES`/`INCOME_CATEGORY_NAMES`/
  `INVESTMENT_LINKED_CATEGORIES` deixaram de ser listas fixas e viraram funções
  (`expense_category_names()`, `income_category_names()`, `investment_linked_categories()`) que
  mesclam as 5 fixas com `custom_categories.list_custom_categories()` toda vez que são chamadas
  — sem cache, então uma categoria criada aparece imediatamente na próxima vez que o formulário
  de lançamento abrir, sem precisar reiniciar o app nem de um `rebuild_ui()`.
- **`theme.category_color()`** — categorias sem cor fixa (todas as personalizadas) caem numa
  paleta auxiliar de 8 tons (`_AUTO_CATEGORY_PALETTE`, matizes escolhidos pra não colidir com as
  cores fixas de vermelho/laranja/verde/roxo já usadas), escolhida por um hash determinístico dos
  **bytes UTF-8** do nome (não o `hash()` embutido do Python — esse é randomizado por processo via
  `PYTHONHASHSEED`, daria uma cor diferente a cada vez que o app abrisse). Testado: mesma
  categoria, mesma cor, em processos Python separados.
- **`consumption_chart.py`** — a lógica de fatias já era genérica (itera sobre
  `totals_by_label`, sem número fixo de categorias); só a legenda mudou, de uma coluna única
  (`pack`) pra uma grade (`grid`, `_LEGEND_ROWS_PER_COLUMN = 4`) — com poucas categorias o
  resultado é idêntico a uma coluna; a partir da 5ª, cresce em largura em vez de virar uma lista
  cada vez mais alta.
- **`settings_view.py`** — nova seção "Categorias", mesmo padrão visual da seção "Perfis de cor"
  já existente: formulário pra criar (nome + tipo + comportamento) e lista das categorias
  personalizadas já criadas, cada uma com botão "Remover" (`ConfirmDialog`, mesmo componente já
  usado pra remover perfil de cor). As 5 fixas não aparecem nessa lista — não são removíveis.

## Consequências

- Categoria personalizada só vira uma linha de verdade na tabela `categories` do SQLite na
  primeira vez que um lançamento a usa (preguiçoso, via `findOrCreateByName`) — igual já
  acontecia com as 5 fixas. Remover a categoria personalizada da UI não apaga essa linha nem
  nenhum lançamento; eles continuam mostrando nome e cor normalmente (órfãos, como "Necessário").
- Cor de categoria personalizada é sempre uma das 8 da paleta auxiliar (nunca escolhida à mão
  pelo usuário) — aceitável pro pedido ("as cores podem variar"), mas duas categorias diferentes
  cujos nomes caiam no mesmo slot de hash (`sum(bytes) % 8`) acabam com a mesma cor. Baixo
  impacto esperado (poucas categorias personalizadas na prática) — não resolvido nesta versão.
- Uma categoria personalizada não pode ser usada nos dois tipos (Despesa e Receita) — precisa
  escolher um na criação, igual as fixas hoje (nenhuma das 5 é dual). Se isso incomodar no uso
  real, dá pra reconsiderar depois.
