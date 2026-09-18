#include "sync/HybridLogicalClock.hpp"

#include <stdexcept>

namespace iterador::sync {

HybridLogicalClock::HybridLogicalClock(std::string deviceId) : deviceId_(std::move(deviceId)) {}

std::string HybridLogicalClock::tick() {
    throw std::logic_error("HybridLogicalClock::tick ainda nao implementado");
}

std::string HybridLogicalClock::observe(const std::string&) {
    throw std::logic_error("HybridLogicalClock::observe ainda nao implementado");
}

}  // namespace iterador::sync
