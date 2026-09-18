#pragma once

#include <optional>
#include <vector>

#include "core/Category.hpp"
#include "core/Id.hpp"
#include "storage/Database.hpp"

namespace iterador::storage {

class CategoryRepository {
public:
    CategoryRepository(Database& db, core::EntityId deviceId);

    std::vector<core::Category> listAll();
    std::optional<core::Category> findById(const core::EntityId& id);
    core::Category create(const std::string& name, core::CategoryKind kind);

    // Acha uma categoria existente com esse nome+tipo, ou cria uma nova. Usado pelo fluxo
    // simples de adicionar transação (Application::createTransaction) — aceita qualquer nome
    // vindo de Python, sem validar contra lista fixa nenhuma; é isso que permite a UI oferecer
    // categorias personalizadas (ver UI/iterador_ui/custom_categories.py, ADR-0028) sem
    // precisar de nenhuma mudança aqui.
    core::Category findOrCreateByName(const std::string& name, core::CategoryKind kind);

private:
    Database& db_;
    core::EntityId deviceId_;
};

}  // namespace iterador::storage
