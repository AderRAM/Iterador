#include "storage/BudgetRepository.hpp"

#include <sqlite3.h>

#include <stdexcept>

#include "core/Timestamp.hpp"
#include "storage/OperationLog.hpp"

namespace iterador::storage {

namespace {

core::Budget rowToBudget(sqlite3_stmt* stmt) {
    core::Budget budget;
    budget.id = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 0));
    budget.name = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 1));
    const std::int64_t cents = sqlite3_column_int64(stmt, 2);
    const std::string currency = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 3));
    budget.targetValue = core::Money(cents, currency);
    budget.months = sqlite3_column_int(stmt, 4);
    const unsigned char* investmentId = sqlite3_column_text(stmt, 5);
    budget.investmentId = investmentId ? reinterpret_cast<const char*>(investmentId) : "";
    const std::string createdAt = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 6));
    budget.createdAt = core::fromDateString(createdAt.substr(0, 10));
    return budget;
}

}  // namespace

BudgetRepository::BudgetRepository(Database& db, core::EntityId deviceId)
    : db_(db), deviceId_(std::move(deviceId)) {}

std::vector<core::Budget> BudgetRepository::listAll() {
    std::lock_guard<std::mutex> lock(db_.mutex());

    static const char* kSql =
        "SELECT id, name, target_value_cents, currency, months, investment_id, created_at "
        "FROM budgets;";
    sqlite3_stmt* stmt = nullptr;
    if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
        throw std::runtime_error(std::string("BudgetRepository::listAll prepare: ") +
                                  sqlite3_errmsg(db_.handle()));
    }

    std::vector<core::Budget> budgets;
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        budgets.push_back(rowToBudget(stmt));
    }
    sqlite3_finalize(stmt);
    return budgets;
}

std::optional<core::Budget> BudgetRepository::findById(const core::EntityId& id) {
    std::lock_guard<std::mutex> lock(db_.mutex());

    static const char* kSql =
        "SELECT id, name, target_value_cents, currency, months, investment_id, created_at "
        "FROM budgets WHERE id = ?;";
    sqlite3_stmt* stmt = nullptr;
    if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
        throw std::runtime_error(std::string("BudgetRepository::findById prepare: ") +
                                  sqlite3_errmsg(db_.handle()));
    }
    sqlite3_bind_text(stmt, 1, id.c_str(), -1, SQLITE_TRANSIENT);

    std::optional<core::Budget> result;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        result = rowToBudget(stmt);
    }
    sqlite3_finalize(stmt);
    return result;
}

core::Budget BudgetRepository::create(const std::string& name, std::int64_t targetValueCents,
                                       const std::string& currency, int months,
                                       const core::EntityId& investmentId) {
    core::Budget budget;
    budget.id = core::generateUuid();
    budget.name = name;
    budget.targetValue = core::Money(targetValueCents, currency);
    budget.months = months;
    budget.investmentId = investmentId;
    budget.createdAt = core::now();

    {
        std::lock_guard<std::mutex> lock(db_.mutex());
        static const char* kSql =
            "INSERT INTO budgets "
            "(id, name, target_value_cents, currency, months, investment_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?);";
        sqlite3_stmt* stmt = nullptr;
        if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
            throw std::runtime_error(std::string("BudgetRepository::create prepare: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        sqlite3_bind_text(stmt, 1, budget.id.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_text(stmt, 2, budget.name.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_int64(stmt, 3, budget.targetValue.cents());
        sqlite3_bind_text(stmt, 4, budget.targetValue.currency().c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_int(stmt, 5, budget.months);
        if (budget.investmentId.empty()) {
            sqlite3_bind_null(stmt, 6);
        } else {
            sqlite3_bind_text(stmt, 6, budget.investmentId.c_str(), -1, SQLITE_TRANSIENT);
        }
        sqlite3_bind_text(stmt, 7, core::toIso8601(budget.createdAt).c_str(), -1,
                           SQLITE_TRANSIENT);

        const int rc = sqlite3_step(stmt);
        sqlite3_finalize(stmt);
        if (rc != SQLITE_DONE) {
            throw std::runtime_error(std::string("BudgetRepository::create step: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
    }

    const std::string timestamp = core::toIso8601(core::now());
    OperationLog(db_).append(OperationLogEntry{
        .opId = core::generateUuid(),
        .deviceId = deviceId_,
        .entityType = "budget",
        .entityId = budget.id,
        .opType = "CREATE",
        .payloadJson = R"({"name":")" + budget.name + R"("})",
        .hlc = timestamp,
        .appliedAt = timestamp,
    });

    return budget;
}

core::Budget BudgetRepository::update(const core::EntityId& id, const std::string& name,
                                       std::int64_t targetValueCents, const std::string& currency,
                                       int months, const core::EntityId& investmentId) {
    const auto existing = findById(id);
    if (!existing) {
        throw std::runtime_error("BudgetRepository::update: id nao encontrado: " + id);
    }

    core::Budget budget;
    budget.id = id;
    budget.name = name;
    budget.targetValue = core::Money(targetValueCents, currency);
    budget.months = months;
    budget.investmentId = investmentId;
    budget.createdAt = existing->createdAt;

    {
        std::lock_guard<std::mutex> lock(db_.mutex());
        static const char* kSql =
            "UPDATE budgets SET name = ?, target_value_cents = ?, currency = ?, months = ?, "
            "investment_id = ? WHERE id = ?;";
        sqlite3_stmt* stmt = nullptr;
        if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
            throw std::runtime_error(std::string("BudgetRepository::update prepare: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        sqlite3_bind_text(stmt, 1, budget.name.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_int64(stmt, 2, budget.targetValue.cents());
        sqlite3_bind_text(stmt, 3, budget.targetValue.currency().c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_int(stmt, 4, budget.months);
        if (budget.investmentId.empty()) {
            sqlite3_bind_null(stmt, 5);
        } else {
            sqlite3_bind_text(stmt, 5, budget.investmentId.c_str(), -1, SQLITE_TRANSIENT);
        }
        sqlite3_bind_text(stmt, 6, budget.id.c_str(), -1, SQLITE_TRANSIENT);

        const int rc = sqlite3_step(stmt);
        const int changes = sqlite3_changes(db_.handle());
        sqlite3_finalize(stmt);
        if (rc != SQLITE_DONE) {
            throw std::runtime_error(std::string("BudgetRepository::update step: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        if (changes == 0) {
            throw std::runtime_error("BudgetRepository::update: id nao encontrado: " + id);
        }
    }

    const std::string timestamp = core::toIso8601(core::now());
    OperationLog(db_).append(OperationLogEntry{
        .opId = core::generateUuid(),
        .deviceId = deviceId_,
        .entityType = "budget",
        .entityId = budget.id,
        .opType = "UPDATE",
        .payloadJson = R"({"name":")" + budget.name + R"("})",
        .hlc = timestamp,
        .appliedAt = timestamp,
    });

    return budget;
}

void BudgetRepository::remove(const core::EntityId& id) {
    {
        std::lock_guard<std::mutex> lock(db_.mutex());
        static const char* kSql = "DELETE FROM budgets WHERE id = ?;";
        sqlite3_stmt* stmt = nullptr;
        if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
            throw std::runtime_error(std::string("BudgetRepository::remove prepare: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        sqlite3_bind_text(stmt, 1, id.c_str(), -1, SQLITE_TRANSIENT);

        const int rc = sqlite3_step(stmt);
        const int changes = sqlite3_changes(db_.handle());
        sqlite3_finalize(stmt);
        if (rc != SQLITE_DONE) {
            throw std::runtime_error(std::string("BudgetRepository::remove step: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        if (changes == 0) {
            throw std::runtime_error("BudgetRepository::remove: id nao encontrado: " + id);
        }
    }

    const std::string timestamp = core::toIso8601(core::now());
    OperationLog(db_).append(OperationLogEntry{
        .opId = core::generateUuid(),
        .deviceId = deviceId_,
        .entityType = "budget",
        .entityId = id,
        .opType = "DELETE",
        .payloadJson = "{}",
        .hlc = timestamp,
        .appliedAt = timestamp,
    });
}

void BudgetRepository::clearInvestmentLink(const core::EntityId& investmentId) {
    std::lock_guard<std::mutex> lock(db_.mutex());
    static const char* kSql = "UPDATE budgets SET investment_id = NULL WHERE investment_id = ?;";
    sqlite3_stmt* stmt = nullptr;
    if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
        throw std::runtime_error(std::string("BudgetRepository::clearInvestmentLink prepare: ") +
                                  sqlite3_errmsg(db_.handle()));
    }
    sqlite3_bind_text(stmt, 1, investmentId.c_str(), -1, SQLITE_TRANSIENT);

    const int rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);
    if (rc != SQLITE_DONE) {
        throw std::runtime_error(std::string("BudgetRepository::clearInvestmentLink step: ") +
                                  sqlite3_errmsg(db_.handle()));
    }
    // Sem entrada em OperationLog aqui de propósito, mesmo motivo de
    // TransactionRepository::clearInvestmentLink (afeta N orçamentos de uma vez; sync P2P ainda
    // é stub).
}

}  // namespace iterador::storage
