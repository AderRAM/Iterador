#pragma once

#include <string>

#include "sync/IPeerSource.hpp"

namespace iterador::sync {

// Descoberta via Tailscale (ver Guide/architecture.md). Nesta fase, lê uma lista local
// peers.json com hosts/IPs cadastrados manualmente; automação via `tailscale status --json`
// fica para uma fase futura.
// TODO: implementar leitura de peersConfigPath e handshake TCP periódico com cada peer.
class TailscalePeerSource : public IPeerSource {
public:
    explicit TailscalePeerSource(std::string peersConfigPath);

    std::vector<Peer> discover() override;

private:
    std::string peersConfigPath_;
};

}  // namespace iterador::sync
