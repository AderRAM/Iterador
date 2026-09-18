# 0009 — Editar investimentos + padrão de Caixinha Nubank

Status: Aceito

## Contexto

O usuário apontou duas coisas:

1. Não havia como editar um investimento depois de criado — só criar e listar.
2. Na prática, o investimento que o usuário mais usa é a Caixinha do Nubank, e ele mexe
   constantemente no valor (aportes e resgates). Pediu que, se o usuário não abrir "Mais
   opções" ao criar um investimento, os valores característicos da Caixinha Nubank sejam
   aplicados automaticamente — ou seja, o caminho rápido (Nome + Valor) já devia bastar.

Pesquisei como a Caixinha Nubank funciona antes de decidir os valores padrão: a modalidade
padrão ("RDB de resgate imediato") rende 100% do CDI e não cobra taxa de administração,
custódia nem abertura — só incide IR regressivo sobre o rendimento (fora do escopo do modelo
ainda, ver Roadmap). Fonte: pesquisa registrada no [ADR-0008](0008-fetch-selic-rate-from-bcb.md).

## Decisão

- `InvestmentRepository::update()` (+ `Application::updateInvestment` + binding
  `update_investment` + `backend_bridge.update_investment`) — segue o mesmo padrão de
  `create()`: grava no SQLite e registra uma entrada `UPDATE` em `operation_log`.
- `InvestmentFormDialog` (`UI/iterador_ui/widgets/`) agora serve tanto para criar quanto para
  editar — recebe um `investment` opcional; se vier preenchido, os campos vêm pré-carregados,
  o título vira "Editar investimento", e o botão chama `update_investment` em vez de
  `create_investment`.
- `InvestmentsView` ganhou um botão "Editar" em cada linha da lista.
- Ao **criar** um investimento novo, o campo Tipo já vem preenchido com "Caixinha Nubank", e os
  campos avançados (colapsados) já vêm com os valores padrão dessa modalidade: Taxas = 0%, % da
  Selic/CDI = 100%. Quem só preencher Nome e Valor e enviar já cria um registro correto de
  Caixinha Nubank sem precisar abrir "Mais opções".

## Consequências

- O padrão assume que a maioria dos investimentos cadastrados são Caixinha Nubank — correto
  para o uso atual do usuário, mas se ele passar a usar o app para outros tipos de investimento
  com mais frequência, esse padrão pode precisar mudar (ou virar uma preferência configurável).
- `update()` não distingue "mudei só o valor" de "mudei o tipo/rentabilidade" — qualquer edição
  reescreve a linha inteira. Suficiente para o uso atual (poucos campos, sem histórico de
  auditoria de qual campo mudou); se granularidade por campo for necessária depois, revisitar.
- Segue sem tributação (IR regressivo) e sem distinguir indexador (pós-fixado/prefixado/IPCA+)
  no modelo — apontado no ADR-0008, continua no Roadmap.
