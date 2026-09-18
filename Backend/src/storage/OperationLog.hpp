#pragma once

#include <string>

#include "storage/Database.hpp"

namespace iterador::storage {

// Uma entrada do log de operações — a base do sync P2P (ver Guide/architecture.md). Toda
// mutação feita pelos *Repository grava uma entrada aqui; o módulo sync/ (ainda não
// implementado) só lê/escreve nesta tabela, nunca nas de domínio diretamente.
struct OperationLogEntry {
    std::string opId;
    std::string deviceId;
    std::string entityType;  // ex. "investment", "transaction"
    std::string entityId;
    std::string opType;      // "CREATE" | "UPDATE" | "DELETE"
    std::string payloadJson;
    // Ordena e resolve conflitos entre dispositivos (ADR-0006). Nesta fase, sem o módulo sync/
    // implementado, é preenchido com um timestamp ISO-8601 simples; a geração real via
    // HybridLogicalClock entra quando SyncEngine existir.
    std::string hlc;
    std::string appliedAt;
};

class OperationLog {
public:
    explicit OperationLog(Database& db) : db_(db) {}

    // Grava uma entrada local — chamado por todo *Repository após uma mutação.
    void append(const OperationLogEntry& entry);

    // TODO(sync): aplica uma entrada recebida de outro dispositivo (sem gerar novo log local).
    // Depende de SyncProtocol/SyncEngine — ver Guide/architecture.md → Roadmap.
    void applyRemoteOperation(const OperationLogEntry& entry);

private:
    Database& db_;
};

}  // namespace iterador::storage
