#pragma once

#include <mutex>
#include <string>

struct sqlite3;
struct sqlite3_stmt;

namespace iterador::storage {

// RAII sobre uma conexão SQLite. Roda migrations pendentes na abertura. Protegida por mutex
// interno porque é acessada tanto pela thread principal (chamadas vindas da UI via Application)
// quanto pela thread de sync (SyncEngine) — ver Guide/architecture.md.
class Database {
public:
    explicit Database(const std::string& path);
    ~Database();

    Database(const Database&) = delete;
    Database& operator=(const Database&) = delete;

    // Executa SQL sem parâmetros nem resultado (ex. DDL, migrations).
    void exec(const std::string& sql);

    // RAII de transação: começa no construtor, faz commit no destrutor a menos que rollback()
    // tenha sido chamado.
    class Transaction {
    public:
        explicit Transaction(Database& db);
        ~Transaction();
        void rollback();

    private:
        Database& db_;
        bool rolledBack_ = false;
    };

    sqlite3* handle() { return handle_; }
    std::mutex& mutex() { return mutex_; }

private:
    void runMigrations();
    int currentUserVersion();
    void setUserVersion(int version);

    sqlite3* handle_ = nullptr;
    std::mutex mutex_;
};

}  // namespace iterador::storage
