#include "core/Money.hpp"

#include <stdexcept>

namespace iterador::core {

Money::Money(std::int64_t cents, std::string currency)
    : cents_(cents), currency_(std::move(currency)) {}

void Money::checkSameCurrency(const Money& other) const {
    if (currency_ != other.currency_) {
        throw std::invalid_argument(
            "Money: operacao entre moedas diferentes (" + currency_ + " vs " + other.currency_ + ")");
    }
}

Money Money::operator+(const Money& other) const {
    checkSameCurrency(other);
    return Money(cents_ + other.cents_, currency_);
}

Money Money::operator-(const Money& other) const {
    checkSameCurrency(other);
    return Money(cents_ - other.cents_, currency_);
}

bool Money::operator==(const Money& other) const {
    return currency_ == other.currency_ && cents_ == other.cents_;
}

bool Money::operator<(const Money& other) const {
    checkSameCurrency(other);
    return cents_ < other.cents_;
}

}  // namespace iterador::core
