#pragma once

#include <atomic>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "storage/Database.hpp"
#include "sync/IPeerSource.hpp"
#include "sync/SyncConfig.hpp"

namespace iterador::sync {

struct SyncStatus {
    bool running = false;
    int knownPeers = 0;
    std::string lastSyncAt;  // ISO-8601, vazio se nunca sincronizou.
    std::string lastError;
};

// Orquestra descoberta de peers -> conexão -> troca de operation_log -> aplicação local, numa
// thread própria dentro do processo (ver Guide/architecture.md). Regra importante: esta classe
// NUNCA chama de volta para dentro do Tk/CustomTkinter — a UI consulta status() por polling.
// TODO: implementar o laço da thread (descoberta periódica, handshake TCP, troca de
// OPLOG_REQUEST/OPLOG_BATCH via SyncProtocol, aplicação via OperationLog::applyRemoteOperation).
class SyncEngine {
public:
    SyncEngine(storage::Database& db, SyncConfig config,
               std::vector<std::unique_ptr<IPeerSource>> peerSources);
    ~SyncEngine();

    void start();
    void stop();
    SyncStatus status() const;

private:
    storage::Database& db_;
    SyncConfig config_;
    std::vector<std::unique_ptr<IPeerSource>> peerSources_;

    std::thread worker_;
    std::atomic<bool> running_{false};
    mutable std::mutex statusMutex_;
    SyncStatus status_;
};

}  // namespace iterador::sync
