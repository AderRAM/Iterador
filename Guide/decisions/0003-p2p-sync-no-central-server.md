# 0003 — Sincronização P2P sem servidor central

Status: Aceito

## Contexto

O Iterador precisa sincronizar dados entre até 3 dispositivos (Linux, Windows, Android) via LAN
ou Tailscale. Duas abordagens possíveis: um dispositivo atua como servidor central e os outros
como clientes finos (dependem da rede para funcionar), ou cada dispositivo é autônomo e
sincroniza par a par quando encontra outro.

## Decisão

Modelo **peer-to-peer**: cada dispositivo roda seu próprio backend com banco SQLite local
completo, funciona 100% offline, e sincroniza mudanças com outros dispositivos quando os
encontra na LAN ou via Tailscale — sem nenhum servidor central obrigatório.

## Consequências

- Nenhum dispositivo precisa estar sempre ligado para os outros funcionarem.
- Exige um protocolo de sincronização com resolução de conflito (ver
  [`0006-hybrid-logical-clock-lww-conflict-resolution.md`](0006-hybrid-logical-clock-lww-conflict-resolution.md)),
  mais complexo do que um servidor com uma verdade única.
- Descoberta de peers precisa de dois mecanismos distintos: broadcast UDP em LAN e uma lista
  conhecida de hosts para Tailscale (ver `Backend/src/sync/PeerDiscovery.*` e
  `TailscalePeerSource.*`).
- Segurança do tráfego de sync assume a rede (LAN local/Tailscale) como perímetro já confiável
  nesta fase — autenticação/criptografia do protocolo fica para um ADR futuro quando isso for
  endereçado.
