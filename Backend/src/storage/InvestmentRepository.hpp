#pragma once

#include <cstdint>
#include <optional>
#include <vector>

#include "core/Id.hpp"
#include "core/Investment.hpp"
#include "storage/Database.hpp"

namespace iterador::storage {

// CRUD de investimentos. Segue o mesmo padrão que AccountRepository seguia antes de ser
// removido (ver Guide/decisions/0007-remove-account-add-investment.md): mapear linha SQLite <->
// struct de core/, gravar em operation_log a cada mutação.
class InvestmentRepository {
public:
    InvestmentRepository(Database& db, core::EntityId deviceId);

    std::vector<core::Investment> listAll();
    std::optional<core::Investment> findById(const core::EntityId& id);
    core::Investment create(const std::string& name, const std::string& type,
                             std::int64_t currentValueCents, const std::string& currency,
                             double yieldRate, double feesRate, double selicPercentage);

    // Edição — usuário mexe com frequência no valor (aportes/resgates) e ocasionalmente no
    // tipo/rentabilidade de um investimento já existente.
    core::Investment update(const core::EntityId& id, const std::string& name,
                             const std::string& type, std::int64_t currentValueCents,
                             const std::string& currency, double yieldRate, double feesRate,
                             double selicPercentage);

    // Remove um investimento. Quem chama (Application::deleteInvestment) já desvinculou
    // transações/orçamentos que apontavam pra ele antes de chamar isso — a coluna
    // investment_id nessas tabelas tem FK ON investments(id) com foreign_keys=ON, então apagar
    // com vínculos ainda ativos falharia com um erro de constraint.
    void remove(const core::EntityId& id);

private:
    Database& db_;
    core::EntityId deviceId_;
};

}  // namespace iterador::storage
