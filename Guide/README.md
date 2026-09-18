# Guide

Esta pasta é a base de conhecimento viva do projeto Iterador — o lugar para entender o projeto
sem precisar ler todo o código, e para manter contexto entre sessões de desenvolvimento
(humanas ou de assistentes de IA).

A organização segue o framework [Diataxis](https://diataxis.fr/) (4 tipos de documentação) mais
Architecture Decision Records (ADRs) para decisões técnicas:

| Arquivo/pasta | Tipo (Diataxis) | Conteúdo |
|---|---|---|
| [`usage.md`](usage.md) | Tutorial / How-to | Como configurar o ambiente, buildar, rodar, testar, e resolver problemas comuns |
| [`dev-practices.md`](dev-practices.md) | Explanation | Técnicas de desenvolvimento usadas no projeto (verificação, isolamento de dados, armadilhas do CustomTkinter, etc.) — não o quê, o **como** |
| [`architecture.md`](architecture.md) | Explanation | Como as peças se encaixam, por quê, e o que falta implementar |
| [`file-map.md`](file-map.md) | Reference | Onde fica cada arquivo e para que serve |
| [`functions.md`](functions.md) | Reference | API pública exposta ao Python (o que chamar, sem precisar ler o C++) |
| [`decisions/`](decisions/) | ADRs | Uma decisão técnica por arquivo, com contexto e consequências |
| [`spreadsheet-reference.md`](spreadsheet-reference.md) | Reference | Estrutura real da planilha Excel do usuário — base do importador já implementado (ver ADR-0023) |
| [`checklist.md`](checklist.md) | Reference | Tarefas concluídas e pendentes do projeto |

## Como manter isso atualizado

Regra simples: **o código e o Guide mudam juntos, no mesmo commit.**

- Novo arquivo, arquivo removido, ou arquivo movido em `Backend/` ou `UI/` → atualize a linha
  correspondente em `file-map.md`.
- Método novo/alterado/removido na API exposta ao Python (`Application` em C++, ou
  `backend_bridge.py`) → atualize `functions.md`.
- Decisão técnica não-óbvia (troca de biblioteca, formato de protocolo, modelo de dados) → um
  ADR novo em `decisions/000X-titulo-curto.md`. **Nunca edite um ADR antigo** — se uma decisão
  for substituída, o ADR antigo ganha `Status: Superseded by ADR-000Y` e o novo ADR referencia o
  antigo.
- Mudou o fluxo de setup/build/run? → `usage.md`.
- Terminou ou começou uma tarefa? → risque/adicione em `checklist.md`.
- Mudou a arquitetura geral (nova camada, novo componente, mudança no modelo de sync)? →
  `architecture.md`, inclusive a seção "Roadmap" no final, que lista o que ainda não foi
  implementado.

Este processo não é uma invenção específica do projeto — é a combinação de práticas comuns:
`docs/` estilo Diataxis, ADRs (padrão popularizado por Michael Nygard, usado em times como
ThoughtWorks e Spotify), e a convenção mais recente de um `CLAUDE.md`/`AGENTS.md` na raiz do
projeto para dar contexto persistente a assistentes de IA — ver [`../CLAUDE.md`](../CLAUDE.md).
