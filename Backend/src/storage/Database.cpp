#include "storage/Database.hpp"

#include <sqlite3.h>

#include <stdexcept>

#include "generated/EmbeddedMigrations.hpp"

namespace iterador::storage {

namespace {

void checkOk(int rc, sqlite3* handle, const std::string& context) {
    if (rc != SQLITE_OK && rc != SQLITE_DONE && rc != SQLITE_ROW) {
        throw std::runtime_error(context + ": " + sqlite3_errmsg(handle));
    }
}

}  // namespace

Database::Database(const std::string& path) {
    if (sqlite3_open(path.c_str(), &handle_) != SQLITE_OK) {
        const std::string message = handle_ ? sqlite3_errmsg(handle_) : "falha desconhecida";
        sqlite3_close(handle_);
        throw std::runtime_error("Database: nao foi possivel abrir '" + path + "': " + message);
    }
    exec("PRAGMA foreign_keys = ON;");
    runMigrations();
}

Database::~Database() {
    if (handle_) {
        sqlite3_close(handle_);
    }
}

void Database::exec(const std::string& sql) {
    std::lock_guard<std::mutex> lock(mutex_);
    char* errorMessage = nullptr;
    const int rc = sqlite3_exec(handle_, sql.c_str(), nullptr, nullptr, &errorMessage);
    if (rc != SQLITE_OK) {
        std::string message = errorMessage ? errorMessage : "erro desconhecido";
        sqlite3_free(errorMessage);
        throw std::runtime_error("Database::exec falhou: " + message);
    }
}

int Database::currentUserVersion() {
    sqlite3_stmt* stmt = nullptr;
    checkOk(sqlite3_prepare_v2(handle_, "PRAGMA user_version;", -1, &stmt, nullptr), handle_,
            "prepare user_version");
    int version = 0;
    if (sqlite3_step(stmt) == SQLITE_ROW) {
        version = sqlite3_column_int(stmt, 0);
    }
    sqlite3_finalize(stmt);
    return version;
}

void Database::setUserVersion(int version) {
    exec("PRAGMA user_version = " + std::to_string(version) + ";");
}

void Database::runMigrations() {
    // Cada migration é lida de src/storage/migrations/*.sql e embutida no binário pelo CMake
    // (ver generated/EmbeddedMigrations.hpp). Novas migrations entram aqui como mais um bloco
    // "if (currentUserVersion() < N) { ...; setUserVersion(N); }" — nunca alterar uma migration
    // já aplicada em produção, só adicionar a próxima.
    if (currentUserVersion() < 1) {
        exec(migrations::kMigration0001Init);
        setUserVersion(1);
    }
    if (currentUserVersion() < 2) {
        exec(migrations::kMigration0002LinkTransactionInvestment);
        setUserVersion(2);
    }
    if (currentUserVersion() < 3) {
        exec(migrations::kMigration0003RedesignBudgetsAsGoals);
        setUserVersion(3);
    }
    if (currentUserVersion() < 4) {
        exec(migrations::kMigration0004AddTransactionSortOrder);
        setUserVersion(4);
    }
    if (currentUserVersion() < 5) {
        exec(migrations::kMigration0005AddTransactionRecurringFlag);
        setUserVersion(5);
    }
}

Database::Transaction::Transaction(Database& db) : db_(db) {
    db_.exec("BEGIN;");
}

Database::Transaction::~Transaction() {
    if (!rolledBack_) {
        db_.exec("COMMIT;");
    }
}

void Database::Transaction::rollback() {
    if (!rolledBack_) {
        db_.exec("ROLLBACK;");
        rolledBack_ = true;
    }
}

}  // namespace iterador::storage
