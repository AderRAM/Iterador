# 0046 — Corrigida corrida de inicialização entre `set_widget_scaling` e `geometry`/`minsize`

Status: Aceito

## Contexto

Relato do usuário: depois de maximizar a janela principal, não conseguia mais diminuí-la — a
decoração da janela (KDE/Wayland, via XWayland) mostrava só o botão de fechar, sem
maximizar/restaurar. Reproduzido de ponta a ponta num ambiente isolado (Xvfb + `kwin_x11` real,
banco de teste em `/tmp`, nunca `~/.iterador/iterador.db`) — não bastava simular resize por fora
(isso funcionava), precisou instrumentar `IteradorApp` de verdade com pontos de diagnóstico
(`_current_width`/`_min_width`/`_max_width`, `wm_geometry()`, `wm minsize()`, `wm maxsize()`) em
vários instantes depois de abrir, igual à técnica de "diagnóstico por medição real" já usada no
projeto (ver ADR-0026).

## Causa raiz

`IteradorApp.__init__` (`UI/iterador_ui/app.py`) chamava, nessa ordem:

```python
ctk.set_widget_scaling(preferences.load_ui_scale())  # ANTES
self.geometry("1200x900")
self.minsize(900, 600)
```

`CTk._set_scaling()` (interno do CustomTkinter, `ctk_tk.py`) tem um hack documentado no próprio
código-fonte da lib ("Force new dimensions on window by using min, max... without min, max it
won't work"): toda vez que a escala é aplicada, ele trava `minsize == maxsize == tamanho ATUAL
da janela` por ~1 segundo (`self.after(1000, self._set_scaled_min_max)` desfaz depois).

Como `set_widget_scaling` era chamado **antes** de `self.geometry("1200x900")`, o "tamanho
atual" que esse hack via era o default do CTk (600×500), não o que o Iterador queria. Resultado
medido, instrumentando a app real:

- `wm_geometry` abria em **900×600** (não 1200×900) — ficava permanentemente preso nesse
  tamanho, mesmo depois do hack se autocorrigir (o Tk corrige os limites min/max sozinho depois
  de ~1s, mas **não** redimensiona a janela de volta — quem já encolheu, fica encolhido).
- Durante esse ~1s inicial, `WM_NORMAL_HINTS` chegava a ficar com `minsize(900,600) >
  maxsize(600,500)` — combinação inválida. Confirmado via `xprop`: nesse estado,
  `_NET_WM_ALLOWED_ACTIONS` do KWin **não incluía** `_NET_WM_ACTION_RESIZE` nem
  `_NET_WM_ACTION_MAXIMIZE_HORZ`/`_NET_WM_ACTION_MAXIMIZE_VERT` — o WM via a janela como
  não-redimensionável e escondia os botões de maximizar/restaurar da decoração, batendo com o
  relato do usuário (só o X aparecia).

Interessante: confirmado que o **KWin recomputa `_NET_WM_ALLOWED_ACTIONS` dinamicamente** quando
os hints relaxam depois (os botões voltam by ~1-1.5s) — então o sintoma mais persistente/
reproduzível não é "botão nunca mais volta", é a janela abrir sempre pequena demais (900×600, o
mínimo) e ficar assim, mais uma janela real (embora estreita) de alguns instantes com a
decoração "quebrada" logo na abertura — provavelmente mais perceptível em máquinas mais lentas
ou bancos maiores (a construção da janela já mede ~868ms com dado sintético, ver Roadmap de
performance no `checklist.md`), tempo próximo o suficiente do ~1s do hack pra frequentemente
coincidir com o usuário mexendo na janela.

## Decisão: inverter a ordem — geometria real antes da escala

```python
self.title("Iterador")
self.geometry("1200x900")
self.minsize(900, 600)

ctk.set_widget_scaling(preferences.load_ui_scale())
```

Com isso, quando `_set_scaling()` roda o hack, o "tamanho atual" já É 1200×900 (o que o Iterador
realmente quer) — o travamento temporário fica em `minsize == maxsize == 1200×900` (consistente,
sem inversão), e a autocorreção ~1s depois só relaxa pra `minsize(900,600)`/`maxsize(~ilimitado)`
sem nunca ter encolhido a janela. Validado instrumentando a app real de novo com os mesmos pontos
de diagnóstico: `wm_geometry` fica em 1200×900 desde o primeiro instante e continua assim depois
da autocorreção; ciclo completo maximizar → restaurar → redimensionar manualmente testado depois
via protocolo EWMH (mesmo mecanismo que o botão de maximizar da decoração usa) — funciona em
todos os pontos.

## Consequências

- Fix de 3 linhas reordenadas em `app.py`, sem mudança de comportamento visível pretendido (a
  janela sempre deveria abrir em 1200×900).
- Nenhuma mudança no CustomTkinter (biblioteca de terceiros) — o hack em si continua existindo lá,
  só deixamos de alimentá-lo com o tamanho errado.
- Não reproduzido no ambiente real do usuário (Wayland/KDE) por mim — testado em X11 puro
  (`kwin_x11`) via Xvfb, que já é suficiente pra confirmar a causa raiz (a lógica de hints/ações
  é a mesma; XWayland pode ter timing levemente diferente). Usuário deve confirmar que o
  problema não volta a acontecer no uso real.
