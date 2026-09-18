# 0002 — Backend em C++ exposto à UI via pybind11

Status: Aceito

## Contexto

O usuário definiu C++ para o backend e CustomTkinter (Python) para a UI desktop. É preciso
decidir como esses dois mundos se comunicam dentro do mesmo dispositivo: um processo servidor
local (HTTP/gRPC) chamado pela UI, ou o C++ compilado diretamente como extensão Python.

## Decisão

Usar **pybind11**: o backend C++ é compilado como um módulo de extensão Python
(`iterador_core`), importado e chamado diretamente pela UI dentro do mesmo processo. Não há
processo servidor separado para uso local — só a UI Python com o C++ carregado nela.

## Consequências

- Comunicação local é uma chamada de função direta (sem serialização de rede, sem overhead de
  processo), mais simples de depurar.
- A superfície exposta ao Python precisa ficar pequena e estável — por isso `Application`
  (`Backend/src/app/`) é a única fachada exposta; `storage/` e `sync/` nunca são expostos
  diretamente (ver [`../functions.md`](../functions.md)).
- Um futuro app Android nativo (`App/`) **não** pode reusar este binding diretamente (pybind11 é
  específico de Python) — ele vai precisar de sua própria forma de acessar o backend (compilar o
  core para Android via NDK, ou falar por rede com um dispositivo desktop). Isso é aceitável
  porque Android foi explicitamente adiado para fase futura.
- Build fica acoplado ao CMake + pybind11 (ver `Backend/cmake/Dependencies.cmake`).
