#include "core/Category.hpp"

#include <stdexcept>

namespace iterador::core {

std::string toString(CategoryKind kind) {
    switch (kind) {
        case CategoryKind::Income: return "INCOME";
        case CategoryKind::Expense: return "EXPENSE";
    }
    throw std::invalid_argument("CategoryKind invalido");
}

CategoryKind categoryKindFromString(const std::string& value) {
    if (value == "INCOME") return CategoryKind::Income;
    if (value == "EXPENSE") return CategoryKind::Expense;
    throw std::invalid_argument("CategoryKind desconhecido: " + value);
}

}  // namespace iterador::core
