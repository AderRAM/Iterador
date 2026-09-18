#include "core/Transaction.hpp"

#include <stdexcept>

namespace iterador::core {

std::string toString(TransactionType type) {
    switch (type) {
        case TransactionType::Income: return "INCOME";
        case TransactionType::Expense: return "EXPENSE";
        case TransactionType::Transfer: return "TRANSFER";
    }
    throw std::invalid_argument("TransactionType invalido");
}

TransactionType transactionTypeFromString(const std::string& value) {
    if (value == "INCOME") return TransactionType::Income;
    if (value == "EXPENSE") return TransactionType::Expense;
    if (value == "TRANSFER") return TransactionType::Transfer;
    throw std::invalid_argument("TransactionType desconhecido: " + value);
}

std::string toString(TransactionStatus status) {
    switch (status) {
        case TransactionStatus::Pending: return "PENDING";
        case TransactionStatus::Paid: return "PAID";
    }
    throw std::invalid_argument("TransactionStatus invalido");
}

TransactionStatus transactionStatusFromString(const std::string& value) {
    if (value == "PENDING") return TransactionStatus::Pending;
    if (value == "PAID") return TransactionStatus::Paid;
    throw std::invalid_argument("TransactionStatus desconhecido: " + value);
}

}  // namespace iterador::core
