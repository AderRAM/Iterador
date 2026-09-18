#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include <doctest/doctest.h>

#include "core/Money.hpp"

using iterador::core::Money;

TEST_CASE("Money soma valores na mesma moeda") {
    Money a(1000, "BRL");
    Money b(250, "BRL");
    CHECK((a + b).cents() == 1250);
}

TEST_CASE("Money subtrai valores na mesma moeda") {
    Money a(1000, "BRL");
    Money b(250, "BRL");
    CHECK((a - b).cents() == 750);
}

TEST_CASE("Money compara igualdade por centavos e moeda") {
    CHECK(Money(500, "BRL") == Money(500, "BRL"));
    CHECK_FALSE(Money(500, "BRL") == Money(500, "USD"));
}

TEST_CASE("Money lanca excecao ao operar entre moedas diferentes") {
    Money a(1000, "BRL");
    Money b(1000, "USD");
    CHECK_THROWS_AS((void)(a + b), std::invalid_argument);
}
