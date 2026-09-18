#pragma once

#include <pybind11/pybind11.h>

namespace iterador::bindings {

// Expõe Money e Investment (core/) ao módulo Python.
void bindCore(pybind11::module_& module);

}  // namespace iterador::bindings
