# 0001 — Registrar decisões de arquitetura em ADRs

Status: Aceito

## Contexto

O projeto vai crescer ao longo de várias sessões de desenvolvimento (por um humano e por
assistentes de IA). Decisões técnicas não-óbvias (por que pybind11 e não outra opção, por que
P2P e não servidor central, etc.) precisam ficar registradas com o raciocínio por trás, não só
o resultado — senão são refeitas ou revertidas sem contexto.

## Decisão

Usar Architecture Decision Records (ADRs) no formato Nygard simplificado (Título / Status /
Contexto / Decisão / Consequências), um arquivo por decisão em `Guide/decisions/`, numerados
sequencialmente. ADRs antigos nunca são editados — se uma decisão é substituída, o ADR antigo
ganha `Status: Superseded by ADR-000X` e o novo ADR referencia o antigo.

## Consequências

- Qualquer pessoa (ou IA) entrando no projeto entende o "porquê", não só o "o quê".
- Exige disciplina de criar um ADR sempre que uma decisão técnica não-óbvia for tomada — regra
  documentada em [`../README.md`](../README.md) e em [`../../CLAUDE.md`](../../CLAUDE.md).
