#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "bindings/bind_app.hpp"
#include "bindings/bind_core.hpp"

namespace py = pybind11;

PYBIND11_MODULE(iterador_core, m) {
    m.doc() = "Iterador — backend C++ (core, storage, sync) exposto ao Python via pybind11";

    iterador::bindings::bindCore(m);
    iterador::bindings::bindApp(m);
}
