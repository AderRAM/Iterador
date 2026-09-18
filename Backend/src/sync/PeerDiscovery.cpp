#include "sync/PeerDiscovery.hpp"

namespace iterador::sync {

PeerDiscovery::PeerDiscovery(SyncConfig config) : config_(std::move(config)) {}

std::vector<Peer> PeerDiscovery::discover() {
    // TODO: broadcast UDP em config_.lanDiscoveryPort — ver PeerDiscovery.hpp e
    // Guide/architecture.md → Roadmap.
    return {};
}

}  // namespace iterador::sync
