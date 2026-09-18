#include "storage/OperationLog.hpp"

#include <sqlite3.h>

#include <stdexcept>

namespace iterador::storage {

void OperationLog::append(const OperationLogEntry& entry) {
    std::lock_guard<std::mutex> lock(db_.mutex());

    static const char* kSql =
        "INSERT INTO operation_log "
        "(op_id, device_id, entity_type, entity_id, op_type, payload_json, hlc, applied_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?);";

    sqlite3_stmt* stmt = nullptr;
    if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
        throw std::runtime_error(std::string("OperationLog::append prepare: ") +
                                  sqlite3_errmsg(db_.handle()));
    }

    sqlite3_bind_text(stmt, 1, entry.opId.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 2, entry.deviceId.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 3, entry.entityType.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 4, entry.entityId.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 5, entry.opType.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 6, entry.payloadJson.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 7, entry.hlc.c_str(), -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 8, entry.appliedAt.c_str(), -1, SQLITE_TRANSIENT);

    const int rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);
    if (rc != SQLITE_DONE) {
        throw std::runtime_error(std::string("OperationLog::append step: ") +
                                  sqlite3_errmsg(db_.handle()));
    }
}

void OperationLog::applyRemoteOperation(const OperationLogEntry&) {
    // TODO(sync): implementar junto com SyncEngine (ver Guide/architecture.md → Roadmap).
    throw std::logic_error("OperationLog::applyRemoteOperation ainda nao implementado");
}

}  // namespace iterador::storage
