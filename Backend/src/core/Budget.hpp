#pragma once

#include <string>

#include "core/Id.hpp"
#include "core/Money.hpp"
#include "core/Timestamp.hpp"

namespace iterador::core {

// Meta de economia (aba "Orçamentos" na UI) — não é limite de gasto por categoria, é "quanto eu
// preciso guardar por mês pra juntar X em N meses" (ver ADR-0017). Pode opcionalmente estar
// ligada a um Investment (o dinheiro acumulado fica investido enquanto junta).
struct Budget {
    EntityId id;
    std::string name;         // ex. "Viagem", "Notebook novo"
    Money targetValue;        // valor total do item
    int months = 1;            // em quantos meses dividir
    EntityId investmentId;     // opcional, "" = nenhum
    Timestamp createdAt;
};

}  // namespace iterador::core
