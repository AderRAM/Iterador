#pragma once

#include <cstdint>
#include <string>

namespace iterador::sync {

// Configuração do sync P2P para este dispositivo (ver Guide/architecture.md).
struct SyncConfig {
    std::string deviceName = "Iterador Device";
    std::uint16_t lanDiscoveryPort = 53317;
    std::uint16_t syncPort = 53318;
    int discoveryIntervalSeconds = 5;
    int peerExpirySeconds = 30;
    bool enabled = false;  // desligado por padrão nesta fase (sync ainda não implementado).
};

}  // namespace iterador::sync
