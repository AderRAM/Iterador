#include "bindings/bind_app.hpp"

#include <pybind11/stl.h>

#include "app/Application.hpp"
#include "sync/SyncEngine.hpp"

namespace py = pybind11;

namespace iterador::bindings {

void bindApp(py::module_& module) {
    using iterador::app::Application;
    using iterador::sync::SyncStatus;

    py::class_<SyncStatus>(module, "SyncStatus")
        .def_readonly("running", &SyncStatus::running)
        .def_readonly("known_peers", &SyncStatus::knownPeers)
        .def_readonly("last_sync_at", &SyncStatus::lastSyncAt)
        .def_readonly("last_error", &SyncStatus::lastError);

    py::class_<Application>(module, "Application")
        .def(py::init<const std::string&>(), py::arg("db_path"))
        .def("list_investments", &Application::listInvestments)
        .def("create_investment", &Application::createInvestment, py::arg("name"),
             py::arg("type"), py::arg("current_value_cents"), py::arg("currency"),
             py::arg("yield_rate"), py::arg("fees_rate"), py::arg("selic_percentage"))
        .def("update_investment", &Application::updateInvestment, py::arg("id"), py::arg("name"),
             py::arg("type"), py::arg("current_value_cents"), py::arg("currency"),
             py::arg("yield_rate"), py::arg("fees_rate"), py::arg("selic_percentage"))
        .def("delete_investment", &Application::deleteInvestment, py::arg("id"))
        .def("list_transactions", &Application::listTransactions)
        .def("create_transaction", &Application::createTransaction, py::arg("description"),
             py::arg("category_name"), py::arg("type"), py::arg("amount_cents"),
             py::arg("currency"), py::arg("status"), py::arg("occurred_at_date"),
             py::arg("investment_id"))
        .def("update_transaction", &Application::updateTransaction, py::arg("id"),
             py::arg("description"), py::arg("category_name"), py::arg("type"),
             py::arg("amount_cents"), py::arg("currency"), py::arg("status"),
             py::arg("occurred_at_date"), py::arg("investment_id"))
        .def("set_transaction_status", &Application::setTransactionStatus, py::arg("id"),
             py::arg("status"))
        .def("update_transaction_sort_order", &Application::updateTransactionSortOrder,
             py::arg("id"), py::arg("sort_order"))
        .def("update_transaction_recurring", &Application::updateTransactionRecurring,
             py::arg("id"), py::arg("is_recurring"))
        .def("delete_transaction", &Application::deleteTransaction, py::arg("id"))
        .def("list_budgets", &Application::listBudgets)
        .def("create_budget", &Application::createBudget, py::arg("name"),
             py::arg("target_value_cents"), py::arg("currency"), py::arg("months"),
             py::arg("investment_id"))
        .def("update_budget", &Application::updateBudget, py::arg("id"), py::arg("name"),
             py::arg("target_value_cents"), py::arg("currency"), py::arg("months"),
             py::arg("investment_id"))
        .def("delete_budget", &Application::deleteBudget, py::arg("id"))
        .def("start_sync", &Application::startSync)
        .def("stop_sync", &Application::stopSync)
        .def("sync_status", &Application::syncStatus);
}

}  // namespace iterador::bindings
