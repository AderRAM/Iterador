#include "sync/SyncEngine.hpp"

namespace iterador::sync {

SyncEngine::SyncEngine(storage::Database& db, SyncConfig config,
                        std::vector<std::unique_ptr<IPeerSource>> peerSources)
    : db_(db), config_(std::move(config)), peerSources_(std::move(peerSources)) {}

SyncEngine::~SyncEngine() {
    stop();
}

void SyncEngine::start() {
    // TODO: iniciar worker_ com o laço de descoberta/sync — ver SyncEngine.hpp e
    // Guide/architecture.md → Roadmap. Por ora só marca o status como "rodando", sem rede real.
    std::lock_guard<std::mutex> lock(statusMutex_);
    running_ = true;
    status_.running = true;
}

void SyncEngine::stop() {
    running_ = false;
    if (worker_.joinable()) {
        worker_.join();
    }
    std::lock_guard<std::mutex> lock(statusMutex_);
    status_.running = false;
}

SyncStatus SyncEngine::status() const {
    std::lock_guard<std::mutex> lock(statusMutex_);
    return status_;
}

}  // namespace iterador::sync
