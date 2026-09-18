#pragma once

#include "sync/IPeerSource.hpp"
#include "sync/SyncConfig.hpp"

namespace iterador::sync {

// Descoberta de peers em LAN via broadcast/multicast UDP (ver Guide/architecture.md).
// TODO: implementar — anunciar {device_id, device_name, app_version, sync_port} periodicamente
// e manter tabela peer->último-visto, expirando após SyncConfig::peerExpirySeconds.
class PeerDiscovery : public IPeerSource {
public:
    explicit PeerDiscovery(SyncConfig config);

    std::vector<Peer> discover() override;

private:
    SyncConfig config_;
};

}  // namespace iterador::sync
