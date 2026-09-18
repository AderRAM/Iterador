#pragma once

#include <optional>
#include <vector>

#include "core/Id.hpp"
#include "core/Transaction.hpp"
#include "storage/Database.hpp"

namespace iterador::storage {

class TransactionRepository {
public:
    TransactionRepository(Database& db, core::EntityId deviceId);

    std::vector<core::Transaction> listAll();
    std::optional<core::Transaction> findById(const core::EntityId& id);
    // occurredAtDate: "YYYY-MM-DD". Editável pelo usuário na UI, mas por padrão vem preenchido
    // com o dia atual (quem decide o default é a UI, não o repositório). investmentId vazio =
    // transação não afeta nenhum investimento.
    core::Transaction create(const core::EntityId& categoryId, core::TransactionType type,
                              std::int64_t amountCents, const std::string& currency,
                              const std::string& description, const std::string& occurredAtDate,
                              const core::EntityId& investmentId,
                              core::TransactionStatus status = core::TransactionStatus::Pending);

    // Marca uma transação existente como paga/pendente (ex. "a pagar" -> "pago"). Usado pelo
    // botão de alternar status rápido na lista, sem precisar abrir o formulário de edição.
    core::Transaction setStatus(const core::EntityId& id, core::TransactionStatus status);

    // Reatribui a ordem manual de exibição (ver core::Transaction::sortOrder). A UI calcula o
    // valor (indexação fracionária entre os vizinhos do arrasto) — este método só grava, sem
    // lógica de negócio, igual setStatus().
    core::Transaction updateSortOrder(const core::EntityId& id, double sortOrder);

    // Fixa/desfixa (ícone de pin, ver core::Transaction::isRecurring) — só grava, igual
    // setStatus()/updateSortOrder(). A lógica de clonar pro mês novo mora na UI (Python), que já
    // sabe quais transações estão fixadas via list_transactions().
    core::Transaction updateRecurring(const core::EntityId& id, bool isRecurring);

    // Edição geral (descrição, valor, tipo, status, data, investimento) — usuário edita
    // lançamentos com frequência.
    core::Transaction update(const core::EntityId& id, const core::EntityId& categoryId,
                              core::TransactionType type, std::int64_t amountCents,
                              const std::string& currency, const std::string& description,
                              core::TransactionStatus status, const std::string& occurredAtDate,
                              const core::EntityId& investmentId);

    // Remove uma transação (ex. lançamento adicionado por engano).
    void remove(const core::EntityId& id);

    // Desvincula toda transação que apontava pra esse investimento (investment_id vira NULL —
    // "nenhum investimento vinculado", mesmo estado de quando o usuário escolhe "Nenhum
    // (genérico)" no formulário, ver ADR-0022). Usado por Application::deleteInvestment antes de
    // apagar o investimento: a transação em si não é apagada, só perde o vínculo — mesmo
    // princípio de nunca destruir lançamento histórico por causa da remoção de outra entidade.
    void clearInvestmentLink(const core::EntityId& investmentId);

private:
    Database& db_;
    core::EntityId deviceId_;
};

}  // namespace iterador::storage
