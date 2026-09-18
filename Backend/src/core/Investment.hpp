#pragma once

#include <string>

#include "core/Id.hpp"
#include "core/Money.hpp"

namespace iterador::core {

// Um investimento nomeado pelo usuário (ex. "Tesouro Selic", "CDB Itaú", "Ações XYZ") — não é
// uma "conta": não existe sistema de múltiplas contas no Iterador, só uma carteira implícita.
// Dinheiro (saldo líquido) e Investimento são os dois "baldes" onde o valor do usuário fica.
// Ver Guide/decisions/0007-remove-account-add-investment.md.
//
// yieldRate/feesRate/selicPercentage ficam como percentuais em ponto flutuante (ex. 12.5 =
// 12,5%) — formato é um primeiro rascunho, a confirmar com o usuário (ver Guide/architecture.md
// > Roadmap): não está definido ainda se são taxas ao ano, ao mês, ou "% do CDI/Selic" como é
// comum em renda fixa brasileira.
struct Investment {
    EntityId id;
    std::string name;      // nome dado pelo usuário
    std::string type;      // tipo definido pelo usuário (texto livre nesta fase, ex. "Renda fixa")
    Money currentValue;    // quanto está investido/vale hoje
    double yieldRate = 0.0;       // rentabilidade (%, formato a confirmar)
    double feesRate = 0.0;        // taxas (%, ex. taxa de administração)
    double selicPercentage = 0.0; // quanto rende em relação à Selic (ex. 110 = 110% da Selic/CDI)
};

}  // namespace iterador::core
