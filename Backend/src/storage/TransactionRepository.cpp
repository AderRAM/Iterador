#include "storage/TransactionRepository.hpp"

#include <sqlite3.h>

#include <stdexcept>

#include "core/Timestamp.hpp"
#include "storage/OperationLog.hpp"

namespace iterador::storage {

namespace {

// SQLite retorna nullptr de sqlite3_column_text() para uma coluna NULL — investment_id é
// opcional (transação pode não afetar nenhum investimento).
std::string textOrEmpty(sqlite3_stmt* stmt, int column) {
    const unsigned char* value = sqlite3_column_text(stmt, column);
    return value ? reinterpret_cast<const char*>(value) : "";
}

core::Transaction rowToTransaction(sqlite3_stmt* stmt) {
    core::Transaction transaction;
    transaction.id = textOrEmpty(stmt, 0);
    transaction.categoryId = textOrEmpty(stmt, 1);
    transaction.type = core::transactionTypeFromString(textOrEmpty(stmt, 2));
    transaction.status = core::transactionStatusFromString(textOrEmpty(stmt, 3));
    const std::int64_t cents = sqlite3_column_int64(stmt, 4);
    transaction.amount = core::Money(cents, textOrEmpty(stmt, 5));
    transaction.description = textOrEmpty(stmt, 6);
    transaction.occurredAt = core::fromDateString(textOrEmpty(stmt, 7).substr(0, 10));
    transaction.investmentId = textOrEmpty(stmt, 8);
    transaction.categoryName = textOrEmpty(stmt, 9);
    transaction.sortOrder = sqlite3_column_double(stmt, 10);
    transaction.isRecurring = sqlite3_column_int(stmt, 11) != 0;
    return transaction;
}

const char* kSelectColumns =
    "t.id, t.category_id, t.type, t.status, t.amount_cents, t.currency, t.description, "
    "t.occurred_at, t.investment_id, c.name, t.sort_order, t.is_recurring";

}  // namespace

TransactionRepository::TransactionRepository(Database& db, core::EntityId deviceId)
    : db_(db), deviceId_(std::move(deviceId)) {}

std::vector<core::Transaction> TransactionRepository::listAll() {
    std::lock_guard<std::mutex> lock(db_.mutex());

    const std::string sql = std::string("SELECT ") + kSelectColumns +
                             " FROM transactions t JOIN categories c ON c.id = t.category_id "
                             "ORDER BY t.sort_order DESC;";
    sqlite3_stmt* stmt = nullptr;
    if (sqlite3_prepare_v2(db_.handle(), sql.c_str(), -1, &stmt, nullptr) != SQLITE_OK) {
        throw std::runtime_error(std::string("TransactionRepository::listAll prepare: ") +
                                  sqlite3_errmsg(db_.handle()));
    }

    std::vector<core::Transaction> transactions;
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        transactions.push_back(rowToTransaction(stmt));
    }
    sqlite3_finalize(stmt);
    return transactions;
}

std::optional<core::Transaction> TransactionRepository::findById(const core::EntityId& id) {
    std::lock_guard<std::mutex> lock(db_.mutex());

    const std::string sql = std::string("SELECT ") + kSelectColumns +
                             " FROM transactions t JOIN categories c ON c.id = t.category_id "
                             "WHERE t.id = ?;";
    sqlite3_stmt* stmt = nullptr;
    if (sqlite3_prepare_v2(db_.handle(), sql.c_str(), -1, &stmt, nullptr) != SQLITE_OK) {
        throw std::runtime_error(std::string("TransactionRepository::findById prepare: ") +
                                  sqlite3_errmsg(db_.handle()));
    }
    sqlite3_bind_text(stmt, 1, id.c_str(), -1, SQLITE_TRANSIENT);

    std::optional<core::Transaction> result;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        result = rowToTransaction(stmt);
    }
    sqlite3_finalize(stmt);
    return result;
}

namespace {

// investmentId pode ser vazio ("" = NULL na coluna) — sqlite3_bind_text com string vazia grava
// '' (texto vazio), não NULL, então usamos sqlite3_bind_null explicitamente quando vazio.
void bindOptionalText(sqlite3_stmt* stmt, int index, const std::string& value) {
    if (value.empty()) {
        sqlite3_bind_null(stmt, index);
    } else {
        sqlite3_bind_text(stmt, index, value.c_str(), -1, SQLITE_TRANSIENT);
    }
}

}  // namespace

core::Transaction TransactionRepository::create(const core::EntityId& categoryId,
                                                  core::TransactionType type,
                                                  std::int64_t amountCents,
                                                  const std::string& currency,
                                                  const std::string& description,
                                                  const std::string& occurredAtDate,
                                                  const core::EntityId& investmentId,
                                                  core::TransactionStatus status) {
    core::Transaction transaction;
    transaction.id = core::generateUuid();
    transaction.categoryId = categoryId;
    transaction.type = type;
    transaction.status = status;
    transaction.amount = core::Money(amountCents, currency);
    transaction.description = description;
    transaction.occurredAt = core::fromDateString(occurredAtDate);
    transaction.investmentId = investmentId;

    {
        std::lock_guard<std::mutex> lock(db_.mutex());

        // Todo lançamento novo nasce no topo da lista (maior sort_order) — preserva o
        // comportamento de "o mais novo aparece primeiro" mesmo sem o usuário arrastar nada
        // manualmente (ver Guide/decisions/0033-transaction-manual-reorder.md).
        double nextSortOrder = 1.0;
        {
            static const char* kMaxSortOrderSql = "SELECT COALESCE(MAX(sort_order), 0) FROM transactions;";
            sqlite3_stmt* maxStmt = nullptr;
            if (sqlite3_prepare_v2(db_.handle(), kMaxSortOrderSql, -1, &maxStmt, nullptr) != SQLITE_OK) {
                throw std::runtime_error(std::string("TransactionRepository::create prepare max: ") +
                                          sqlite3_errmsg(db_.handle()));
            }
            if (sqlite3_step(maxStmt) == SQLITE_ROW) {
                nextSortOrder = sqlite3_column_double(maxStmt, 0) + 1.0;
            }
            sqlite3_finalize(maxStmt);
        }
        transaction.sortOrder = nextSortOrder;

        static const char* kSql =
            "INSERT INTO transactions "
            "(id, category_id, type, status, amount_cents, currency, description, occurred_at, "
            "investment_id, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);";
        sqlite3_stmt* stmt = nullptr;
        if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
            throw std::runtime_error(std::string("TransactionRepository::create prepare: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        sqlite3_bind_text(stmt, 1, transaction.id.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_text(stmt, 2, transaction.categoryId.c_str(), -1, SQLITE_TRANSIENT);
        const std::string typeStr = core::toString(transaction.type);
        sqlite3_bind_text(stmt, 3, typeStr.c_str(), -1, SQLITE_TRANSIENT);
        const std::string statusStr = core::toString(transaction.status);
        sqlite3_bind_text(stmt, 4, statusStr.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_int64(stmt, 5, transaction.amount.cents());
        sqlite3_bind_text(stmt, 6, transaction.amount.currency().c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_text(stmt, 7, transaction.description.c_str(), -1, SQLITE_TRANSIENT);
        const std::string occurredAtStr = core::toIso8601(transaction.occurredAt);
        sqlite3_bind_text(stmt, 8, occurredAtStr.c_str(), -1, SQLITE_TRANSIENT);
        bindOptionalText(stmt, 9, transaction.investmentId);
        sqlite3_bind_double(stmt, 10, transaction.sortOrder);

        const int rc = sqlite3_step(stmt);
        sqlite3_finalize(stmt);
        if (rc != SQLITE_DONE) {
            throw std::runtime_error(std::string("TransactionRepository::create step: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
    }

    const std::string timestamp = core::toIso8601(core::now());
    OperationLog(db_).append(OperationLogEntry{
        .opId = core::generateUuid(),
        .deviceId = deviceId_,
        .entityType = "transaction",
        .entityId = transaction.id,
        .opType = "CREATE",
        .payloadJson = R"({"description":")" + transaction.description + R"("})",
        .hlc = timestamp,
        .appliedAt = timestamp,
    });

    auto created = findById(transaction.id);
    if (!created) {
        throw std::runtime_error("TransactionRepository::create: id sumiu apos insert: " +
                                  transaction.id);
    }
    return *created;
}

core::Transaction TransactionRepository::setStatus(const core::EntityId& id,
                                                     core::TransactionStatus status) {
    {
        std::lock_guard<std::mutex> lock(db_.mutex());
        static const char* kSql = "UPDATE transactions SET status = ? WHERE id = ?;";
        sqlite3_stmt* stmt = nullptr;
        if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
            throw std::runtime_error(std::string("TransactionRepository::setStatus prepare: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        const std::string statusStr = core::toString(status);
        sqlite3_bind_text(stmt, 1, statusStr.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_text(stmt, 2, id.c_str(), -1, SQLITE_TRANSIENT);

        const int rc = sqlite3_step(stmt);
        const int changes = sqlite3_changes(db_.handle());
        sqlite3_finalize(stmt);
        if (rc != SQLITE_DONE) {
            throw std::runtime_error(std::string("TransactionRepository::setStatus step: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        if (changes == 0) {
            throw std::runtime_error("TransactionRepository::setStatus: id nao encontrado: " + id);
        }
    }

    auto updated = findById(id);
    if (!updated) {
        throw std::runtime_error("TransactionRepository::setStatus: id sumiu apos update: " + id);
    }

    const std::string timestamp = core::toIso8601(core::now());
    OperationLog(db_).append(OperationLogEntry{
        .opId = core::generateUuid(),
        .deviceId = deviceId_,
        .entityType = "transaction",
        .entityId = id,
        .opType = "UPDATE",
        .payloadJson = R"({"status":")" + core::toString(status) + R"("})",
        .hlc = timestamp,
        .appliedAt = timestamp,
    });

    return *updated;
}

core::Transaction TransactionRepository::updateSortOrder(const core::EntityId& id,
                                                           double sortOrder) {
    {
        std::lock_guard<std::mutex> lock(db_.mutex());
        static const char* kSql = "UPDATE transactions SET sort_order = ? WHERE id = ?;";
        sqlite3_stmt* stmt = nullptr;
        if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
            throw std::runtime_error(std::string("TransactionRepository::updateSortOrder prepare: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        sqlite3_bind_double(stmt, 1, sortOrder);
        sqlite3_bind_text(stmt, 2, id.c_str(), -1, SQLITE_TRANSIENT);

        const int rc = sqlite3_step(stmt);
        const int changes = sqlite3_changes(db_.handle());
        sqlite3_finalize(stmt);
        if (rc != SQLITE_DONE) {
            throw std::runtime_error(std::string("TransactionRepository::updateSortOrder step: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        if (changes == 0) {
            throw std::runtime_error("TransactionRepository::updateSortOrder: id nao encontrado: " + id);
        }
    }

    auto updated = findById(id);
    if (!updated) {
        throw std::runtime_error("TransactionRepository::updateSortOrder: id sumiu apos update: " + id);
    }

    const std::string timestamp = core::toIso8601(core::now());
    OperationLog(db_).append(OperationLogEntry{
        .opId = core::generateUuid(),
        .deviceId = deviceId_,
        .entityType = "transaction",
        .entityId = id,
        .opType = "UPDATE",
        .payloadJson = R"({"sort_order":)" + std::to_string(sortOrder) + "}",
        .hlc = timestamp,
        .appliedAt = timestamp,
    });

    return *updated;
}

core::Transaction TransactionRepository::updateRecurring(const core::EntityId& id,
                                                            bool isRecurring) {
    {
        std::lock_guard<std::mutex> lock(db_.mutex());
        static const char* kSql = "UPDATE transactions SET is_recurring = ? WHERE id = ?;";
        sqlite3_stmt* stmt = nullptr;
        if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
            throw std::runtime_error(std::string("TransactionRepository::updateRecurring prepare: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        sqlite3_bind_int(stmt, 1, isRecurring ? 1 : 0);
        sqlite3_bind_text(stmt, 2, id.c_str(), -1, SQLITE_TRANSIENT);

        const int rc = sqlite3_step(stmt);
        const int changes = sqlite3_changes(db_.handle());
        sqlite3_finalize(stmt);
        if (rc != SQLITE_DONE) {
            throw std::runtime_error(std::string("TransactionRepository::updateRecurring step: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        if (changes == 0) {
            throw std::runtime_error("TransactionRepository::updateRecurring: id nao encontrado: " + id);
        }
    }

    auto updated = findById(id);
    if (!updated) {
        throw std::runtime_error("TransactionRepository::updateRecurring: id sumiu apos update: " + id);
    }

    const std::string timestamp = core::toIso8601(core::now());
    OperationLog(db_).append(OperationLogEntry{
        .opId = core::generateUuid(),
        .deviceId = deviceId_,
        .entityType = "transaction",
        .entityId = id,
        .opType = "UPDATE",
        .payloadJson = std::string(R"({"is_recurring":)") + (isRecurring ? "true" : "false") + "}",
        .hlc = timestamp,
        .appliedAt = timestamp,
    });

    return *updated;
}

core::Transaction TransactionRepository::update(const core::EntityId& id,
                                                  const core::EntityId& categoryId,
                                                  core::TransactionType type,
                                                  std::int64_t amountCents,
                                                  const std::string& currency,
                                                  const std::string& description,
                                                  core::TransactionStatus status,
                                                  const std::string& occurredAtDate,
                                                  const core::EntityId& investmentId) {
    {
        std::lock_guard<std::mutex> lock(db_.mutex());
        static const char* kSql =
            "UPDATE transactions SET category_id = ?, type = ?, status = ?, amount_cents = ?, "
            "currency = ?, description = ?, occurred_at = ?, investment_id = ? WHERE id = ?;";
        sqlite3_stmt* stmt = nullptr;
        if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
            throw std::runtime_error(std::string("TransactionRepository::update prepare: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        sqlite3_bind_text(stmt, 1, categoryId.c_str(), -1, SQLITE_TRANSIENT);
        const std::string typeStr = core::toString(type);
        sqlite3_bind_text(stmt, 2, typeStr.c_str(), -1, SQLITE_TRANSIENT);
        const std::string statusStr = core::toString(status);
        sqlite3_bind_text(stmt, 3, statusStr.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_int64(stmt, 4, amountCents);
        sqlite3_bind_text(stmt, 5, currency.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_text(stmt, 6, description.c_str(), -1, SQLITE_TRANSIENT);
        const std::string occurredAtStr = core::toIso8601(core::fromDateString(occurredAtDate));
        sqlite3_bind_text(stmt, 7, occurredAtStr.c_str(), -1, SQLITE_TRANSIENT);
        bindOptionalText(stmt, 8, investmentId);
        sqlite3_bind_text(stmt, 9, id.c_str(), -1, SQLITE_TRANSIENT);

        const int rc = sqlite3_step(stmt);
        const int changes = sqlite3_changes(db_.handle());
        sqlite3_finalize(stmt);
        if (rc != SQLITE_DONE) {
            throw std::runtime_error(std::string("TransactionRepository::update step: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        if (changes == 0) {
            throw std::runtime_error("TransactionRepository::update: id nao encontrado: " + id);
        }
    }

    auto updated = findById(id);
    if (!updated) {
        throw std::runtime_error("TransactionRepository::update: id sumiu apos update: " + id);
    }

    const std::string timestamp = core::toIso8601(core::now());
    OperationLog(db_).append(OperationLogEntry{
        .opId = core::generateUuid(),
        .deviceId = deviceId_,
        .entityType = "transaction",
        .entityId = id,
        .opType = "UPDATE",
        .payloadJson = R"({"description":")" + description + R"("})",
        .hlc = timestamp,
        .appliedAt = timestamp,
    });

    return *updated;
}

void TransactionRepository::remove(const core::EntityId& id) {
    {
        std::lock_guard<std::mutex> lock(db_.mutex());
        static const char* kSql = "DELETE FROM transactions WHERE id = ?;";
        sqlite3_stmt* stmt = nullptr;
        if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
            throw std::runtime_error(std::string("TransactionRepository::remove prepare: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        sqlite3_bind_text(stmt, 1, id.c_str(), -1, SQLITE_TRANSIENT);

        const int rc = sqlite3_step(stmt);
        const int changes = sqlite3_changes(db_.handle());
        sqlite3_finalize(stmt);
        if (rc != SQLITE_DONE) {
            throw std::runtime_error(std::string("TransactionRepository::remove step: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        if (changes == 0) {
            throw std::runtime_error("TransactionRepository::remove: id nao encontrado: " + id);
        }
    }

    const std::string timestamp = core::toIso8601(core::now());
    OperationLog(db_).append(OperationLogEntry{
        .opId = core::generateUuid(),
        .deviceId = deviceId_,
        .entityType = "transaction",
        .entityId = id,
        .opType = "DELETE",
        .payloadJson = "{}",
        .hlc = timestamp,
        .appliedAt = timestamp,
    });
}

void TransactionRepository::clearInvestmentLink(const core::EntityId& investmentId) {
    std::lock_guard<std::mutex> lock(db_.mutex());
    static const char* kSql =
        "UPDATE transactions SET investment_id = NULL WHERE investment_id = ?;";
    sqlite3_stmt* stmt = nullptr;
    if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
        throw std::runtime_error(std::string("TransactionRepository::clearInvestmentLink prepare: ") +
                                  sqlite3_errmsg(db_.handle()));
    }
    sqlite3_bind_text(stmt, 1, investmentId.c_str(), -1, SQLITE_TRANSIENT);

    const int rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);
    if (rc != SQLITE_DONE) {
        throw std::runtime_error(std::string("TransactionRepository::clearInvestmentLink step: ") +
                                  sqlite3_errmsg(db_.handle()));
    }
    // Sem entrada em OperationLog aqui de propósito — afeta N transações de uma vez (não uma
    // entidade só), e o sync P2P ainda é stub (ver Guide/architecture.md > Roadmap); revisitar
    // se/quando o sync de verdade existir.
}

}  // namespace iterador::storage
