#include "storage/CategoryRepository.hpp"

#include <sqlite3.h>

#include <stdexcept>

#include "core/Timestamp.hpp"
#include "storage/OperationLog.hpp"

namespace iterador::storage {

namespace {

core::Category rowToCategory(sqlite3_stmt* stmt) {
    core::Category category;
    category.id = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 0));
    category.name = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 1));
    category.kind =
        core::categoryKindFromString(reinterpret_cast<const char*>(sqlite3_column_text(stmt, 2)));
    return category;
}

}  // namespace

CategoryRepository::CategoryRepository(Database& db, core::EntityId deviceId)
    : db_(db), deviceId_(std::move(deviceId)) {}

std::vector<core::Category> CategoryRepository::listAll() {
    std::lock_guard<std::mutex> lock(db_.mutex());

    static const char* kSql = "SELECT id, name, kind FROM categories;";
    sqlite3_stmt* stmt = nullptr;
    if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
        throw std::runtime_error(std::string("CategoryRepository::listAll prepare: ") +
                                  sqlite3_errmsg(db_.handle()));
    }

    std::vector<core::Category> categories;
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        categories.push_back(rowToCategory(stmt));
    }
    sqlite3_finalize(stmt);
    return categories;
}

std::optional<core::Category> CategoryRepository::findById(const core::EntityId& id) {
    std::lock_guard<std::mutex> lock(db_.mutex());

    static const char* kSql = "SELECT id, name, kind FROM categories WHERE id = ?;";
    sqlite3_stmt* stmt = nullptr;
    if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
        throw std::runtime_error(std::string("CategoryRepository::findById prepare: ") +
                                  sqlite3_errmsg(db_.handle()));
    }
    sqlite3_bind_text(stmt, 1, id.c_str(), -1, SQLITE_TRANSIENT);

    std::optional<core::Category> result;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        result = rowToCategory(stmt);
    }
    sqlite3_finalize(stmt);
    return result;
}

core::Category CategoryRepository::create(const std::string& name, core::CategoryKind kind) {
    core::Category category;
    category.id = core::generateUuid();
    category.name = name;
    category.kind = kind;

    {
        std::lock_guard<std::mutex> lock(db_.mutex());
        static const char* kSql = "INSERT INTO categories (id, name, kind) VALUES (?, ?, ?);";
        sqlite3_stmt* stmt = nullptr;
        if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
            throw std::runtime_error(std::string("CategoryRepository::create prepare: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        sqlite3_bind_text(stmt, 1, category.id.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_text(stmt, 2, category.name.c_str(), -1, SQLITE_TRANSIENT);
        const std::string kindStr = core::toString(category.kind);
        sqlite3_bind_text(stmt, 3, kindStr.c_str(), -1, SQLITE_TRANSIENT);

        const int rc = sqlite3_step(stmt);
        sqlite3_finalize(stmt);
        if (rc != SQLITE_DONE) {
            throw std::runtime_error(std::string("CategoryRepository::create step: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
    }

    const std::string timestamp = core::toIso8601(core::now());
    OperationLog(db_).append(OperationLogEntry{
        .opId = core::generateUuid(),
        .deviceId = deviceId_,
        .entityType = "category",
        .entityId = category.id,
        .opType = "CREATE",
        .payloadJson = R"({"name":")" + category.name + R"("})",
        .hlc = timestamp,
        .appliedAt = timestamp,
    });

    return category;
}

core::Category CategoryRepository::findOrCreateByName(const std::string& name,
                                                        core::CategoryKind kind) {
    {
        std::lock_guard<std::mutex> lock(db_.mutex());
        static const char* kSql =
            "SELECT id, name, kind FROM categories WHERE name = ? AND kind = ?;";
        sqlite3_stmt* stmt = nullptr;
        if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
            throw std::runtime_error(std::string("CategoryRepository::findOrCreateByName prepare: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        sqlite3_bind_text(stmt, 1, name.c_str(), -1, SQLITE_TRANSIENT);
        const std::string kindStr = core::toString(kind);
        sqlite3_bind_text(stmt, 2, kindStr.c_str(), -1, SQLITE_TRANSIENT);

        std::optional<core::Category> existing;
        if (sqlite3_step(stmt) == SQLITE_ROW) {
            existing = rowToCategory(stmt);
        }
        sqlite3_finalize(stmt);
        if (existing) {
            return *existing;
        }
    }
    return create(name, kind);
}

}  // namespace iterador::storage
