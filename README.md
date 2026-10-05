# Iterador

Gerenciador de finanças pessoais multiplataforma (Linux, Windows, Android) com sincronização
peer-to-peer entre dispositivos via LAN e Tailscale.

- UI desktop: CustomTkinter (Python)
- Backend: C++ (exposto ao Python via pybind11)
- App Android: `App/` (projeto separado, fase futura)


## Quickstart

```bash
./scripts/setup_dev_env.sh
./scripts/build_backend.sh
./scripts/run_ui.sh
```
