#include "storage/InvestmentRepository.hpp"

#include <sqlite3.h>

#include <stdexcept>

#include "core/Timestamp.hpp"
#include "storage/OperationLog.hpp"

namespace iterador::storage {

namespace {

core::Investment rowToInvestment(sqlite3_stmt* stmt) {
    core::Investment investment;
    investment.id = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 0));
    investment.name = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 1));
    investment.type = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 2));
    const std::int64_t cents = sqlite3_column_int64(stmt, 3);
    const std::string currency = reinterpret_cast<const char*>(sqlite3_column_text(stmt, 4));
    investment.currentValue = core::Money(cents, currency);
    investment.yieldRate = sqlite3_column_double(stmt, 5);
    investment.feesRate = sqlite3_column_double(stmt, 6);
    investment.selicPercentage = sqlite3_column_double(stmt, 7);
    return investment;
}

}  // namespace

InvestmentRepository::InvestmentRepository(Database& db, core::EntityId deviceId)
    : db_(db), deviceId_(std::move(deviceId)) {}

std::vector<core::Investment> InvestmentRepository::listAll() {
    std::lock_guard<std::mutex> lock(db_.mutex());

    static const char* kSql =
        "SELECT id, name, type, current_value_cents, currency, yield_rate, fees_rate, "
        "selic_percentage FROM investments;";
    sqlite3_stmt* stmt = nullptr;
    if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
        throw std::runtime_error(std::string("InvestmentRepository::listAll prepare: ") +
                                  sqlite3_errmsg(db_.handle()));
    }

    std::vector<core::Investment> investments;
    while (sqlite3_step(stmt) == SQLITE_ROW) {
        investments.push_back(rowToInvestment(stmt));
    }
    sqlite3_finalize(stmt);
    return investments;
}

std::optional<core::Investment> InvestmentRepository::findById(const core::EntityId& id) {
    std::lock_guard<std::mutex> lock(db_.mutex());

    static const char* kSql =
        "SELECT id, name, type, current_value_cents, currency, yield_rate, fees_rate, "
        "selic_percentage FROM investments WHERE id = ?;";
    sqlite3_stmt* stmt = nullptr;
    if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
        throw std::runtime_error(std::string("InvestmentRepository::findById prepare: ") +
                                  sqlite3_errmsg(db_.handle()));
    }
    sqlite3_bind_text(stmt, 1, id.c_str(), -1, SQLITE_TRANSIENT);

    std::optional<core::Investment> result;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        result = rowToInvestment(stmt);
    }
    sqlite3_finalize(stmt);
    return result;
}

core::Investment InvestmentRepository::create(const std::string& name, const std::string& type,
                                               std::int64_t currentValueCents,
                                               const std::string& currency, double yieldRate,
                                               double feesRate, double selicPercentage) {
    core::Investment investment;
    investment.id = core::generateUuid();
    investment.name = name;
    investment.type = type;
    investment.currentValue = core::Money(currentValueCents, currency);
    investment.yieldRate = yieldRate;
    investment.feesRate = feesRate;
    investment.selicPercentage = selicPercentage;

    {
        std::lock_guard<std::mutex> lock(db_.mutex());
        static const char* kSql =
            "INSERT INTO investments "
            "(id, name, type, current_value_cents, currency, yield_rate, fees_rate, "
            "selic_percentage) VALUES (?, ?, ?, ?, ?, ?, ?, ?);";
        sqlite3_stmt* stmt = nullptr;
        if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
            throw std::runtime_error(std::string("InvestmentRepository::create prepare: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        sqlite3_bind_text(stmt, 1, investment.id.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_text(stmt, 2, investment.name.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_text(stmt, 3, investment.type.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_int64(stmt, 4, investment.currentValue.cents());
        sqlite3_bind_text(stmt, 5, investment.currentValue.currency().c_str(), -1,
                           SQLITE_TRANSIENT);
        sqlite3_bind_double(stmt, 6, investment.yieldRate);
        sqlite3_bind_double(stmt, 7, investment.feesRate);
        sqlite3_bind_double(stmt, 8, investment.selicPercentage);

        const int rc = sqlite3_step(stmt);
        sqlite3_finalize(stmt);
        if (rc != SQLITE_DONE) {
            throw std::runtime_error(std::string("InvestmentRepository::create step: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
    }

    const std::string timestamp = core::toIso8601(core::now());
    OperationLog(db_).append(OperationLogEntry{
        .opId = core::generateUuid(),
        .deviceId = deviceId_,
        .entityType = "investment",
        .entityId = investment.id,
        .opType = "CREATE",
        .payloadJson = R"({"name":")" + investment.name + R"(","type":")" + investment.type +
                       R"("})",
        .hlc = timestamp,
        .appliedAt = timestamp,
    });

    return investment;
}

core::Investment InvestmentRepository::update(const core::EntityId& id, const std::string& name,
                                               const std::string& type,
                                               std::int64_t currentValueCents,
                                               const std::string& currency, double yieldRate,
                                               double feesRate, double selicPercentage) {
    core::Investment investment;
    investment.id = id;
    investment.name = name;
    investment.type = type;
    investment.currentValue = core::Money(currentValueCents, currency);
    investment.yieldRate = yieldRate;
    investment.feesRate = feesRate;
    investment.selicPercentage = selicPercentage;

    {
        std::lock_guard<std::mutex> lock(db_.mutex());
        static const char* kSql =
            "UPDATE investments SET name = ?, type = ?, current_value_cents = ?, currency = ?, "
            "yield_rate = ?, fees_rate = ?, selic_percentage = ? WHERE id = ?;";
        sqlite3_stmt* stmt = nullptr;
        if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
            throw std::runtime_error(std::string("InvestmentRepository::update prepare: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        sqlite3_bind_text(stmt, 1, investment.name.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_text(stmt, 2, investment.type.c_str(), -1, SQLITE_TRANSIENT);
        sqlite3_bind_int64(stmt, 3, investment.currentValue.cents());
        sqlite3_bind_text(stmt, 4, investment.currentValue.currency().c_str(), -1,
                           SQLITE_TRANSIENT);
        sqlite3_bind_double(stmt, 5, investment.yieldRate);
        sqlite3_bind_double(stmt, 6, investment.feesRate);
        sqlite3_bind_double(stmt, 7, investment.selicPercentage);
        sqlite3_bind_text(stmt, 8, investment.id.c_str(), -1, SQLITE_TRANSIENT);

        const int rc = sqlite3_step(stmt);
        const int changes = sqlite3_changes(db_.handle());
        sqlite3_finalize(stmt);
        if (rc != SQLITE_DONE) {
            throw std::runtime_error(std::string("InvestmentRepository::update step: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        if (changes == 0) {
            throw std::runtime_error("InvestmentRepository::update: id nao encontrado: " + id);
        }
    }

    const std::string timestamp = core::toIso8601(core::now());
    OperationLog(db_).append(OperationLogEntry{
        .opId = core::generateUuid(),
        .deviceId = deviceId_,
        .entityType = "investment",
        .entityId = investment.id,
        .opType = "UPDATE",
        .payloadJson = R"({"name":")" + investment.name + R"(","type":")" + investment.type +
                       R"("})",
        .hlc = timestamp,
        .appliedAt = timestamp,
    });

    return investment;
}

void InvestmentRepository::remove(const core::EntityId& id) {
    {
        std::lock_guard<std::mutex> lock(db_.mutex());
        static const char* kSql = "DELETE FROM investments WHERE id = ?;";
        sqlite3_stmt* stmt = nullptr;
        if (sqlite3_prepare_v2(db_.handle(), kSql, -1, &stmt, nullptr) != SQLITE_OK) {
            throw std::runtime_error(std::string("InvestmentRepository::remove prepare: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        sqlite3_bind_text(stmt, 1, id.c_str(), -1, SQLITE_TRANSIENT);

        const int rc = sqlite3_step(stmt);
        const int changes = sqlite3_changes(db_.handle());
        sqlite3_finalize(stmt);
        if (rc != SQLITE_DONE) {
            throw std::runtime_error(std::string("InvestmentRepository::remove step: ") +
                                      sqlite3_errmsg(db_.handle()));
        }
        if (changes == 0) {
            throw std::runtime_error("InvestmentRepository::remove: id nao encontrado: " + id);
        }
    }

    const std::string timestamp = core::toIso8601(core::now());
    OperationLog(db_).append(OperationLogEntry{
        .opId = core::generateUuid(),
        .deviceId = deviceId_,
        .entityType = "investment",
        .entityId = id,
        .opType = "DELETE",
        .payloadJson = "{}",
        .hlc = timestamp,
        .appliedAt = timestamp,
    });
}

}  // namespace iterador::storage
