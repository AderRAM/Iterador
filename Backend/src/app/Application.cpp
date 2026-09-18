#include "app/Application.hpp"

namespace iterador::app {

Application::Application(const std::string& dbPath)
    : deviceId_(core::generateUuid()),
      db_(dbPath),
      investments_(db_, deviceId_),
      categories_(db_, deviceId_),
      transactions_(db_, deviceId_),
      budgets_(db_, deviceId_),
      syncEngine_(db_, sync::SyncConfig{}, {}) {}

std::vector<core::Investment> Application::listInvestments() {
    return investments_.listAll();
}

core::Investment Application::createInvestment(const std::string& name, const std::string& type,
                                                 std::int64_t currentValueCents,
                                                 const std::string& currency, double yieldRate,
                                                 double feesRate, double selicPercentage) {
    return investments_.create(name, type, currentValueCents, currency, yieldRate, feesRate,
                                selicPercentage);
}

core::Investment Application::updateInvestment(const std::string& id, const std::string& name,
                                                 const std::string& type,
                                                 std::int64_t currentValueCents,
                                                 const std::string& currency, double yieldRate,
                                                 double feesRate, double selicPercentage) {
    return investments_.update(id, name, type, currentValueCents, currency, yieldRate, feesRate,
                                selicPercentage);
}

void Application::deleteInvestment(const std::string& id) {
    transactions_.clearInvestmentLink(id);
    budgets_.clearInvestmentLink(id);
    investments_.remove(id);
}

std::vector<core::Transaction> Application::listTransactions() {
    return transactions_.listAll();
}

void Application::adjustInvestmentValue(const std::string& investmentId,
                                         std::int64_t deltaCents) {
    if (investmentId.empty() || deltaCents == 0) {
        return;
    }
    auto investment = investments_.findById(investmentId);
    if (!investment) {
        return;  // investimento pode ter sido removido nesse meio tempo; nada a ajustar.
    }
    const std::int64_t newValueCents = investment->currentValue.cents() + deltaCents;
    investments_.update(investment->id, investment->name, investment->type, newValueCents,
                         investment->currentValue.currency(), investment->yieldRate,
                         investment->feesRate, investment->selicPercentage);
}

core::Transaction Application::createTransaction(const std::string& description,
                                                   const std::string& categoryName,
                                                   core::TransactionType type,
                                                   std::int64_t amountCents,
                                                   const std::string& currency,
                                                   core::TransactionStatus status,
                                                   const std::string& occurredAtDate,
                                                   const std::string& investmentId) {
    // Fluxo simples (ADR-0010/0012): a categoria vem de uma lista fixa na UI (categoryName), não
    // mais da descrição — achada/criada automaticamente, sem tela de gerenciar categorias ainda.
    const core::CategoryKind kind =
        type == core::TransactionType::Income ? core::CategoryKind::Income : core::CategoryKind::Expense;
    const core::Category category = categories_.findOrCreateByName(categoryName, kind);
    core::Transaction created = transactions_.create(category.id, type, amountCents, currency,
                                                       description, occurredAtDate, investmentId,
                                                       status);
    // Despesa categoria Investimento = saque, subtrai do investimento; receita categoria
    // Passiva = aporte/rendimento, soma. O delta é o valor da transação sem inverter o sinal
    // (despesa já é negativa) — ver ADR-0012.
    adjustInvestmentValue(investmentId, amountCents);
    return created;
}

core::Transaction Application::updateTransaction(const std::string& id,
                                                   const std::string& description,
                                                   const std::string& categoryName,
                                                   core::TransactionType type,
                                                   std::int64_t amountCents,
                                                   const std::string& currency,
                                                   core::TransactionStatus status,
                                                   const std::string& occurredAtDate,
                                                   const std::string& investmentId) {
    // Desfaz o efeito do estado antigo no investimento antigo antes de aplicar o novo — senão
    // editar um lançamento ligado a um investimento deixaria o valor dele inconsistente.
    auto previous = transactions_.findById(id);
    if (previous) {
        adjustInvestmentValue(previous->investmentId, -previous->amount.cents());
    }

    const core::CategoryKind kind =
        type == core::TransactionType::Income ? core::CategoryKind::Income : core::CategoryKind::Expense;
    const core::Category category = categories_.findOrCreateByName(categoryName, kind);
    core::Transaction updated = transactions_.update(id, category.id, type, amountCents, currency,
                                                       description, status, occurredAtDate,
                                                       investmentId);
    adjustInvestmentValue(investmentId, amountCents);
    return updated;
}

core::Transaction Application::setTransactionStatus(const std::string& id,
                                                      core::TransactionStatus status) {
    return transactions_.setStatus(id, status);
}

core::Transaction Application::updateTransactionSortOrder(const std::string& id,
                                                             double sortOrder) {
    return transactions_.updateSortOrder(id, sortOrder);
}

core::Transaction Application::updateTransactionRecurring(const std::string& id,
                                                             bool isRecurring) {
    return transactions_.updateRecurring(id, isRecurring);
}

void Application::deleteTransaction(const std::string& id) {
    auto existing = transactions_.findById(id);
    if (existing) {
        // Reverte o efeito no investimento (se houver) antes de apagar o lançamento.
        adjustInvestmentValue(existing->investmentId, -existing->amount.cents());
    }
    transactions_.remove(id);
}

std::vector<core::Budget> Application::listBudgets() {
    return budgets_.listAll();
}

core::Budget Application::createBudget(const std::string& name, std::int64_t targetValueCents,
                                        const std::string& currency, int months,
                                        const std::string& investmentId) {
    return budgets_.create(name, targetValueCents, currency, months, investmentId);
}

core::Budget Application::updateBudget(const std::string& id, const std::string& name,
                                        std::int64_t targetValueCents, const std::string& currency,
                                        int months, const std::string& investmentId) {
    return budgets_.update(id, name, targetValueCents, currency, months, investmentId);
}

void Application::deleteBudget(const std::string& id) {
    budgets_.remove(id);
}

void Application::startSync() {
    syncEngine_.start();
}

void Application::stopSync() {
    syncEngine_.stop();
}

sync::SyncStatus Application::syncStatus() {
    return syncEngine_.status();
}

}  // namespace iterador::app
