#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace iterador::sync {

struct Peer {
    std::string deviceId;
    std::string deviceName;
    std::string host;
    std::uint16_t port = 0;
};

// Interface comum de descoberta de peers — implementada por PeerDiscovery (LAN) e
// TailscalePeerSource. SyncEngine consulta uma lista de IPeerSource sem saber qual mecanismo
// cada uma usa por trás.
class IPeerSource {
public:
    virtual ~IPeerSource() = default;
    virtual std::vector<Peer> discover() = 0;
};

}  // namespace iterador::sync
