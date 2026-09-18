#include "bindings/bind_core.hpp"

#include <pybind11/operators.h>

#include "core/Budget.hpp"
#include "core/Category.hpp"
#include "core/Investment.hpp"
#include "core/Money.hpp"
#include "core/Timestamp.hpp"
#include "core/Transaction.hpp"

namespace py = pybind11;

namespace iterador::bindings {

void bindCore(py::module_& module) {
    using iterador::core::Budget;
    using iterador::core::Category;
    using iterador::core::CategoryKind;
    using iterador::core::Investment;
    using iterador::core::Money;
    using iterador::core::Transaction;
    using iterador::core::TransactionStatus;
    using iterador::core::TransactionType;

    py::class_<Money>(module, "Money")
        .def(py::init<std::int64_t, std::string>(), py::arg("cents"), py::arg("currency"))
        .def_property_readonly("cents", &Money::cents)
        .def_property_readonly("currency", &Money::currency)
        .def(py::self + py::self)
        .def(py::self - py::self)
        .def(py::self == py::self)
        .def(py::self < py::self);

    py::class_<Investment>(module, "Investment")
        .def_readonly("id", &Investment::id)
        .def_readonly("name", &Investment::name)
        .def_readonly("type", &Investment::type)
        .def_readonly("current_value", &Investment::currentValue)
        .def_readonly("yield_rate", &Investment::yieldRate)
        .def_readonly("fees_rate", &Investment::feesRate)
        .def_readonly("selic_percentage", &Investment::selicPercentage);

    py::class_<Budget>(module, "Budget")
        .def_readonly("id", &Budget::id)
        .def_readonly("name", &Budget::name)
        .def_readonly("target_value", &Budget::targetValue)
        .def_readonly("months", &Budget::months)
        .def_readonly("investment_id", &Budget::investmentId)
        // "YYYY-MM-DD" — mesmo padrão de Transaction::occurred_at.
        .def_property_readonly("created_at", [](const Budget& b) {
            return iterador::core::toIso8601(b.createdAt).substr(0, 10);
        });

    py::enum_<CategoryKind>(module, "CategoryKind")
        .value("INCOME", CategoryKind::Income)
        .value("EXPENSE", CategoryKind::Expense);

    py::class_<Category>(module, "Category")
        .def_readonly("id", &Category::id)
        .def_readonly("name", &Category::name)
        .def_readonly("kind", &Category::kind);

    py::enum_<TransactionType>(module, "TransactionType")
        .value("INCOME", TransactionType::Income)
        .value("EXPENSE", TransactionType::Expense)
        .value("TRANSFER", TransactionType::Transfer);

    py::enum_<TransactionStatus>(module, "TransactionStatus")
        .value("PENDING", TransactionStatus::Pending)
        .value("PAID", TransactionStatus::Paid);

    py::class_<Transaction>(module, "Transaction")
        .def_readonly("id", &Transaction::id)
        .def_readonly("category_id", &Transaction::categoryId)
        .def_readonly("type", &Transaction::type)
        .def_readonly("status", &Transaction::status)
        .def_readonly("amount", &Transaction::amount)
        .def_readonly("description", &Transaction::description)
        .def_readonly("investment_id", &Transaction::investmentId)
        .def_readonly("category_name", &Transaction::categoryName)
        // "YYYY-MM-DD" — só a data (sem hora), o suficiente para o campo de data editável na
        // UI. Ver core::fromDateString/toIso8601.
        .def_property_readonly("occurred_at", [](const Transaction& t) {
            return iterador::core::toIso8601(t.occurredAt).substr(0, 10);
        })
        // Ordem manual de exibição (maior = mais acima) — ver ADR-0033.
        .def_readonly("sort_order", &Transaction::sortOrder)
        // Fixada (ícone de pin) — clonada automaticamente pro mês novo, ver ADR-0034.
        .def_readonly("is_recurring", &Transaction::isRecurring);
}

}  // namespace iterador::bindings
