#pragma once

#include <pybind11/pybind11.h>

namespace iterador::bindings {

// Expõe Application (app/) — a única fachada de negócio visível ao Python.
void bindApp(pybind11::module_& module);

}  // namespace iterador::bindings
