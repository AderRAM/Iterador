#pragma once

#include <cstdint>
#include <mutex>
#include <string>

namespace iterador::sync {

// Hybrid Logical Clock: wall-clock + contador lógico + device_id. Usado para carimbar entradas
// de operation_log e ordená-las entre dispositivos — conflito = HLC maior vence (ADR-0006).
// TODO: implementar tick()/observe() de verdade junto com SyncEngine — hoje o storage/ usa um
// timestamp ISO-8601 simples como placeholder de hlc (ver OperationLog.hpp).
class HybridLogicalClock {
public:
    explicit HybridLogicalClock(std::string deviceId);

    // Avança o relógio para um novo evento local e retorna sua representação serializada.
    std::string tick();

    // Funde o relógio local com um HLC recebido de outro dispositivo (ao receber uma operação
    // remota), preservando a propriedade de que o relógio nunca anda para trás.
    std::string observe(const std::string& remoteHlc);

private:
    std::string deviceId_;
    std::int64_t lastPhysicalMs_ = 0;
    std::uint32_t counter_ = 0;
    std::mutex mutex_;
};

}  // namespace iterador::sync
