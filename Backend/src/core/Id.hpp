#pragma once

#include <cstdint>
#include <iomanip>
#include <random>
#include <sstream>
#include <string>

namespace iterador::core {

using EntityId = std::string;

// UUID v4 simples (não precisa de dependência externa). Usado como id de entidade e como
// device_id no protocolo de sync.
inline EntityId generateUuid() {
    static thread_local std::mt19937_64 rng(std::random_device{}());
    std::uniform_int_distribution<std::uint32_t> byteDist(0, 255);

    std::uint8_t bytes[16];
    for (auto& b : bytes) {
        b = static_cast<std::uint8_t>(byteDist(rng));
    }
    bytes[6] = static_cast<std::uint8_t>((bytes[6] & 0x0F) | 0x40);  // versão 4
    bytes[8] = static_cast<std::uint8_t>((bytes[8] & 0x3F) | 0x80);  // variante RFC 4122

    std::ostringstream out;
    out << std::hex << std::setfill('0');
    for (int i = 0; i < 16; ++i) {
        out << std::setw(2) << static_cast<int>(bytes[i]);
        if (i == 3 || i == 5 || i == 7 || i == 9) {
            out << '-';
        }
    }
    return out.str();
}

}  // namespace iterador::core
