#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "core/Budget.hpp"
#include "core/Investment.hpp"
#include "core/Transaction.hpp"
#include "storage/BudgetRepository.hpp"
#include "storage/CategoryRepository.hpp"
#include "storage/Database.hpp"
#include "storage/InvestmentRepository.hpp"
#include "storage/TransactionRepository.hpp"
#include "sync/SyncEngine.hpp"

namespace iterador::app {

// Fachada única exposta ao Python via pybind11 (ver Backend/src/bindings/). A UI e os bindings
// nunca falam direto com storage:: ou sync:: — só com Application. Isso mantém a fronteira
// C++<->Python pequena e estável (ADR-0002).
class Application {
public:
    explicit Application(const std::string& dbPath);

    // Investimentos — implementado de ponta a ponta (ver storage::InvestmentRepository).
    // Não existe "conta" no Iterador — carteira única/implícita (ver ADR-0007).
    std::vector<core::Investment> listInvestments();
    core::Investment createInvestment(const std::string& name, const std::string& type,
                                       std::int64_t currentValueCents, const std::string& currency,
                                       double yieldRate, double feesRate, double selicPercentage);
    core::Investment updateInvestment(const std::string& id, const std::string& name,
                                       const std::string& type, std::int64_t currentValueCents,
                                       const std::string& currency, double yieldRate,
                                       double feesRate, double selicPercentage);
    // Antes de apagar, desvincula qualquer transação/orçamento que apontava pra este
    // investimento (investment_id vira "" = nenhum, mesmo estado de ADR-0022) — nem lançamento
    // nem meta de economia são apagados por causa disso, só perdem a referência. Sem isso, a FK
    // (foreign_keys=ON) barraria a remoção enquanto existisse qualquer vínculo.
    void deleteInvestment(const std::string& id);

    // Transações — fluxo simples (ver ADR-0010/0012/0014): categoryName é uma categoria fixa
    // da UI (Despesa: Essencial/Lazer/Investimento; Receita: Ativa/Passiva), achada/criada
    // automaticamente — sem tela própria de gerenciar categorias ainda. investmentId (opcional,
    // "" = nenhum) liga a transação a um Investment: despesa+Investimento = saque (subtrai);
    // receita+Passiva = aporte/rendimento (soma) — delta = o próprio amountCents, sem inverter.
    std::vector<core::Transaction> listTransactions();
    // occurredAtDate: "YYYY-MM-DD". A UI já manda preenchido com o dia atual por padrão, mas o
    // usuário pode editar.
    core::Transaction createTransaction(const std::string& description,
                                         const std::string& categoryName,
                                         core::TransactionType type, std::int64_t amountCents,
                                         const std::string& currency, core::TransactionStatus status,
                                         const std::string& occurredAtDate,
                                         const std::string& investmentId);
    core::Transaction updateTransaction(const std::string& id, const std::string& description,
                                         const std::string& categoryName,
                                         core::TransactionType type, std::int64_t amountCents,
                                         const std::string& currency, core::TransactionStatus status,
                                         const std::string& occurredAtDate,
                                         const std::string& investmentId);
    // Alterna pago/pendente rapidamente (ex. botão na própria linha da lista, sem abrir o
    // formulário de edição inteiro).
    core::Transaction setTransactionStatus(const std::string& id, core::TransactionStatus status);
    // Ordem manual de exibição (arrastar na lista, ver ADR-0033) — sortOrder é calculado na UI
    // (indexação fracionária entre os vizinhos do arrasto), este método só grava.
    core::Transaction updateTransactionSortOrder(const std::string& id, double sortOrder);
    // Fixa/desfixa (ícone de pin, ver ADR-0034) — clonagem pro mês novo é decidida pela UI.
    core::Transaction updateTransactionRecurring(const std::string& id, bool isRecurring);
    void deleteTransaction(const std::string& id);

    // Orçamentos (metas de economia, ver core::Budget/ADR-0017): não é limite de gasto, é
    // "junte targetValueCents em months meses" — a UI calcula o aporte mensal (targetValue /
    // months). investmentId opcional ("" = nenhum) só serve pra mostrar/vincular onde o
    // dinheiro acumulado está investido; não move valores automaticamente.
    std::vector<core::Budget> listBudgets();
    core::Budget createBudget(const std::string& name, std::int64_t targetValueCents,
                               const std::string& currency, int months,
                               const std::string& investmentId);
    core::Budget updateBudget(const std::string& id, const std::string& name,
                               std::int64_t targetValueCents, const std::string& currency,
                               int months, const std::string& investmentId);
    void deleteBudget(const std::string& id);

    // Sync — stub nesta fase (ver Guide/architecture.md → Roadmap).
    void startSync();
    void stopSync();
    sync::SyncStatus syncStatus();

private:
    // Soma delta (em centavos) ao valor atual do investimento, preservando os outros campos.
    // delta negativo = investimento perde valor. Usado para manter o investimento consistente
    // quando uma transação ligada a ele é criada/editada/removida (ver ADR-0012). Não faz nada
    // se investmentId estiver vazio.
    void adjustInvestmentValue(const std::string& investmentId, std::int64_t deltaCents);

    // Id gerado uma vez por sessão para identificar este dispositivo nas entradas de
    // operation_log. TODO(sync): persistir entre execuções quando o SyncEngine existir de
    // verdade (ver ADR-0003).
    core::EntityId deviceId_;

    storage::Database db_;
    storage::InvestmentRepository investments_;
    storage::CategoryRepository categories_;
    storage::TransactionRepository transactions_;
    storage::BudgetRepository budgets_;
    sync::SyncEngine syncEngine_;
};

}  // namespace iterador::app
