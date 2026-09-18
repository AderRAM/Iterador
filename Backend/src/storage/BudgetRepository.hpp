#pragma once

#include <cstdint>
#include <optional>
#include <vector>

#include "core/Budget.hpp"
#include "core/Id.hpp"
#include "storage/Database.hpp"

namespace iterador::storage {

// CRUD de metas de economia (ver core::Budget e ADR-0017). Segue o mesmo padrão de
// InvestmentRepository.
class BudgetRepository {
public:
    BudgetRepository(Database& db, core::EntityId deviceId);

    std::vector<core::Budget> listAll();
    std::optional<core::Budget> findById(const core::EntityId& id);
    core::Budget create(const std::string& name, std::int64_t targetValueCents,
                         const std::string& currency, int months,
                         const core::EntityId& investmentId);
    core::Budget update(const core::EntityId& id, const std::string& name,
                         std::int64_t targetValueCents, const std::string& currency, int months,
                         const core::EntityId& investmentId);
    void remove(const core::EntityId& id);

    // Desvincula todo orçamento que apontava pra esse investimento (investment_id vira NULL) —
    // usado por Application::deleteInvestment antes de apagar o investimento. O orçamento em si
    // não é apagado, só perde a referência de onde o dinheiro acumulado estava investido.
    void clearInvestmentLink(const core::EntityId& investmentId);

private:
    Database& db_;
    core::EntityId deviceId_;
};

}  // namespace iterador::storage
