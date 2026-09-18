# 0006 — Hybrid Logical Clock + last-write-wins para conflitos de sync

Status: Aceito

## Contexto

No modelo P2P (ADR-0003), operações feitas em dispositivos diferentes offline precisam ser
ordenadas de forma consistente quando os dispositivos se encontram, para decidir qual versão de
um dado "vence" em caso de conflito. As opções comuns são vector clocks (rastreiam causalidade
completa entre todos os dispositivos) ou um relógio mais simples combinado com last-write-wins.

## Decisão

Usar um **Hybrid Logical Clock (HLC)** — relógio de parede + contador lógico + id do
dispositivo — para carimbar cada entrada de `operation_log`. Em conflito (mesma entidade editada
em dois dispositivos), a entrada com HLC maior vence (last-write-wins).

## Consequências

- Muito mais simples de implementar, persistir e indexar no SQLite do que um vector clock (que
  cresceria um campo por dispositivo já sincronizado).
- Apropriado para o caso de uso real: poucos dispositivos, um único usuário, edição concorrente
  genuína é rara. Não seria a escolha certa para um sistema multiusuário colaborativo com edição
  concorrente frequente — se o projeto crescer nessa direção, isso merece um novo ADR.
- Last-write-wins pode perder uma edição em conflito raro (ex. o mesmo lançamento editado em dois
  dispositivos enquanto ambos estavam offline) — aceitável para a fase atual; não há merge de
  campo a campo nem histórico de versões anteriores.
