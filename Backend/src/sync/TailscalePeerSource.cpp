#include "sync/TailscalePeerSource.hpp"

namespace iterador::sync {

TailscalePeerSource::TailscalePeerSource(std::string peersConfigPath)
    : peersConfigPath_(std::move(peersConfigPath)) {}

std::vector<Peer> TailscalePeerSource::discover() {
    // TODO: ler peersConfigPath_ (peers.json) e tentar handshake TCP com cada host — ver
    // TailscalePeerSource.hpp e Guide/architecture.md → Roadmap.
    return {};
}

}  // namespace iterador::sync
