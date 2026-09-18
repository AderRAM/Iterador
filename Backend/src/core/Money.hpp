#pragma once

#include <cstdint>
#include <string>

namespace iterador::core {

// Valor monetário exato: inteiro em centavos + código de moeda ISO 4217 (ex. "BRL", "USD").
// Nunca usar float/double para dinheiro.
class Money {
public:
    Money() = default;
    Money(std::int64_t cents, std::string currency);

    std::int64_t cents() const { return cents_; }
    const std::string& currency() const { return currency_; }

    Money operator+(const Money& other) const;
    Money operator-(const Money& other) const;
    bool operator==(const Money& other) const;
    bool operator<(const Money& other) const;

private:
    void checkSameCurrency(const Money& other) const;

    std::int64_t cents_ = 0;
    std::string currency_ = "BRL";
};

}  // namespace iterador::core
