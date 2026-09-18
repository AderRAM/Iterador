#include "sync/net/PlatformSocket.hpp"

#include <stdexcept>

#if defined(_WIN32)
// TODO: #include <winsock2.h> / WSAStartup — ver PlatformSocket.hpp.
#else
// TODO: #include <sys/socket.h>, <netinet/in.h>, <unistd.h> — ver PlatformSocket.hpp.
#endif

namespace iterador::sync::net {

PlatformSocket::PlatformSocket() = default;

PlatformSocket::~PlatformSocket() = default;

void PlatformSocket::bindUdp(std::uint16_t) {
    throw std::logic_error("PlatformSocket::bindUdp ainda nao implementado");
}

void PlatformSocket::sendBroadcast(std::uint16_t, const std::string&) {
    throw std::logic_error("PlatformSocket::sendBroadcast ainda nao implementado");
}

std::string PlatformSocket::receive() {
    throw std::logic_error("PlatformSocket::receive ainda nao implementado");
}

}  // namespace iterador::sync::net
