# 0005 — CustomTkinter para a UI desktop (Linux/Windows)

Status: Aceito

## Contexto

O usuário definiu CustomTkinter como framework de UI. CustomTkinter é construído sobre Tkinter,
que não tem runtime para Android — não é possível usar o mesmo código de UI nos três sistemas
operacionais.

## Decisão

CustomTkinter cobre **só a UI desktop (Linux e Windows)** nesta fase. O Android será um app
nativo separado (Kotlin, já scaffolded em `App/`), desenvolvido em fase futura, falando com o
core por outro caminho (NDK e/ou rede) — não reusando o código de `UI/`.

## Consequências

- A UI desktop e a futura UI Android são codebases de interface totalmente separadas — só o
  Backend (via os módulos de `core/`, `storage/`, `sync/`) é compartilhado em espírito, não em
  binário (pybind11 é específico de Python; Android precisaria de seu próprio binding, ex. JNI).
- `UI/` foi estruturada de forma modular (`views/` uma tela por arquivo, `widgets/` componentes
  reutilizáveis, `theme.py` central) para que crescer não vire um único arquivo gigante.
