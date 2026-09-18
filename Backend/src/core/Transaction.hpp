#pragma once

#include <string>

#include "core/Id.hpp"
#include "core/Money.hpp"
#include "core/Timestamp.hpp"

namespace iterador::core {

enum class TransactionType {
    Income,
    Expense,
    // Movimento entre Dinheiro e um Investimento (ex. "Saque investimento" na planilha do
    // usuário) — não existe conta múltipla no Iterador, então Transfer não é entre contas.
    Transfer,
};

std::string toString(TransactionType type);
TransactionType transactionTypeFromString(const std::string& value);

// "A pagar" vs "pago" (ou "a receber" vs "recebido", para Income) — ver Guide/architecture.md
// > Roadmap. Campos adicionais (ex. data de vencimento, data de pagamento, parcelamento,
// recorrência) ainda não foram modelados: dependem de detalhes do fluxo que o usuário ainda vai
// passar. Por ora, occurredAt é usado tanto como data prevista (Pending) quanto data efetiva
// (Paid) — isso deve ser revisitado quando TransactionRepository for implementado de verdade.
enum class TransactionStatus {
    Pending,
    Paid,
};

std::string toString(TransactionStatus status);
TransactionStatus transactionStatusFromString(const std::string& value);

struct Transaction {
    EntityId id;
    EntityId categoryId;
    TransactionType type = TransactionType::Expense;
    TransactionStatus status = TransactionStatus::Pending;
    Money amount;
    std::string description;
    Timestamp occurredAt;
    // Investimento afetado por esta transação (opcional — vazio = nenhum). Ver ADR-0012:
    // categorias fixas (Necessário/Lazer/Investimento) na UI, e quando a categoria é
    // "Investimento" o usuário escolhe qual Investment, que tem o valor ajustado
    // automaticamente (ver Application::createTransaction/updateTransaction/deleteTransaction).
    EntityId investmentId;
    // Nome da categoria (ex. "Necessário") — populado só na leitura via JOIN em
    // TransactionRepository (não é uma fonte de verdade separada; ver Category::name).
    std::string categoryName;
    // Ordem manual de exibição na lista (maior = mais acima) — arrastar na UI reatribui este
    // valor (indexação fracionária, ver Guide/decisions/0033-transaction-manual-reorder.md).
    // Substitui occurredAt como critério principal de TransactionRepository::listAll.
    double sortOrder = 0.0;
    // "Fixada" (ícone de pin na lista) — ao criar um mês novo, é clonada automaticamente pro mês
    // (ver Guide/decisions/0034-recurring-transactions-pin.md). O clone em si nasce com isso
    // false; só o original continua sendo o "molde".
    bool isRecurring = false;
};

}  // namespace iterador::core
