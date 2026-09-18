#pragma once

#include <string>

#include "core/Id.hpp"

namespace iterador::core {

enum class CategoryKind {
    Income,
    Expense,
};

std::string toString(CategoryKind kind);
CategoryKind categoryKindFromString(const std::string& value);

struct Category {
    EntityId id;
    std::string name;
    CategoryKind kind = CategoryKind::Expense;
};

}  // namespace iterador::core
