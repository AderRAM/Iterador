#pragma once

#include <cstdint>
#include <string>

namespace iterador::sync::net {

// Isola toda a diferença entre Winsock (Windows) e sockets BSD (Linux) num único par de
// arquivos — o resto de sync/ é portável e não inclui <winsock2.h>/<sys/socket.h> diretamente.
// TODO: implementar (bind/listen/connect/send/recv para UDP broadcast e TCP) junto com
// PeerDiscovery/SyncEngine — ver Guide/architecture.md → Roadmap.
class PlatformSocket {
public:
    PlatformSocket();
    ~PlatformSocket();

    PlatformSocket(const PlatformSocket&) = delete;
    PlatformSocket& operator=(const PlatformSocket&) = delete;

    void bindUdp(std::uint16_t port);
    void sendBroadcast(std::uint16_t port, const std::string& payload);
    std::string receive();

private:
    int fd_ = -1;
};

}  // namespace iterador::sync::net
