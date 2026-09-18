"""Wiki: explicações de conceitos de finanças usados no app. Ver Guide/file-map.md.

Conteúdo reaproveita a pesquisa já registrada em Guide/decisions/0008-fetch-selic-rate-from-bcb.md
(CDI, Selic, rentabilidade, tributação) mais os conceitos básicos de receita/despesa.

O card "CDI" é especial: além do texto, tem um botão que expande pra mostrar o valor atual
buscado do Banco Central e um gráfico com o histórico dos últimos anos (altos/baixos) — ver
Guide/decisions/0021-cdi-history-from-bcb.md. Fica recolhido e só busca o dado/desenha o
gráfico na primeira expansão, não a cada abertura da Wiki (senão a aba fica pesada de abrir
mesmo pra quem só quer ler o texto).
"""

import threading

import customtkinter as ctk

from iterador_ui import market_data, theme
from iterador_ui.widgets.line_chart import LineChart

_TOPICS = [
    ("Receita", (
        "Dinheiro que entra — ex. salário, venda, recebimento. No Iterador, toda transação "
        "marcada como Receita soma no Total do mês (aba Início)."
    )),
    ("Despesa", (
        "Dinheiro que sai — ex. mercado, contas, lazer. Toda transação marcada como Despesa "
        "subtrai do Total do mês, e entra no gráfico de consumo."
    )),
    ("Selic", (
        "A taxa básica de juros da economia brasileira, definida pelo Copom (Comitê de "
        "Política Monetária do Banco Central). É a referência para quase todo investimento de "
        "renda fixa. O Iterador busca o valor atual dela direto do Banco Central (ver botão "
        "\"Buscar taxa Selic atual\" ao criar/editar um investimento)."
    )),
    ("CDI", (
        "Certificado de Depósito Interbancário — taxa usada entre bancos, que fica bem "
        "próxima da Selic (normalmente um pouco abaixo). É o índice mais comum para investimentos "
        "pós-fixados no Brasil — por isso investimentos costumam ser anunciados como \"rende X% "
        "do CDI\"."
    )),
    ("Rentabilidade", (
        "Quanto um investimento rende, em %. No Iterador, o campo \"Rentabilidade\" de um "
        "investimento serve só para taxa fixa (prefixado — ex. \"rende 12% ao ano\"). Para "
        "investimentos que acompanham o CDI/Selic (a maioria, ex. Caixinha Nubank), quem define "
        "o rendimento é o campo \"% da Selic/CDI\", não a Rentabilidade."
    )),
    ("Pós-fixado vs. prefixado", (
        "Pós-fixado: o rendimento acompanha um índice que varia com o tempo (ex. 100% do CDI) — "
        "não dá pra saber o valor exato no fim antes da hora. Prefixado: a taxa é combinada e "
        "fixa desde o início (ex. 12% ao ano) — dá pra calcular o valor final exato."
    )),
    ("Imposto de Renda (IR) regressivo", (
        "Imposto sobre o rendimento (não sobre o valor total) de investimentos de renda fixa, "
        "que diminui quanto mais tempo o dinheiro fica aplicado: 22,5% até 180 dias, 20% de 181 "
        "a 360 dias, 17,5% de 361 a 720 dias, e 15% acima de 720 dias. Ainda não é calculado "
        "automaticamente pelo Iterador."
    )),
    ("Taxa de administração / custódia", (
        "Taxas que alguns investimentos cobram para existir (comuns em fundos e algumas "
        "corretoras). A Caixinha Nubank, por exemplo, não cobra nenhuma dessas — só o IR sobre "
        "o rendimento."
    )),
]


class WikiView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=theme.BG_APP)

        ctk.CTkLabel(
            self, text="Wiki", font=ctk.CTkFont(size=20, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
        ).pack(anchor="w", padx=24, pady=(24, 8))

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        for title, body in _TOPICS:
            card = ctk.CTkFrame(scroll, fg_color=theme.BG_SURFACE, corner_radius=10,
                                 border_width=1, border_color=theme.INDIGO)
            card.pack(fill="x", pady=6)

            ctk.CTkLabel(
                card, text=title, text_color=theme.ACCENT_HIGHLIGHT,
                font=ctk.CTkFont(size=14, weight="bold"),
            ).pack(anchor="w", padx=14, pady=(10, 2))

            ctk.CTkLabel(
                card, text=body, text_color=theme.TEXT_PRIMARY, justify="left",
                wraplength=680, font=ctk.CTkFont(size=12),
            ).pack(anchor="w", padx=14, pady=(0, 12))

            if title == "CDI":
                self._build_cdi_section(card)

    _CDI_SHOW_TEXT = "▸ Mostrar valor e histórico do CDI"
    _CDI_HIDE_TEXT = "▾ Ocultar valor e histórico do CDI"

    def _build_cdi_section(self, card) -> None:
        # Fica recolhido por padrão — buscar o CDI (rede) e desenhar o histórico (bastante
        # ponto no gráfico) deixava a Wiki pesada pra abrir mesmo pra quem só queria ler o
        # texto. Conteúdo (label + gráfico) só é criado e só busca dado na primeira vez que o
        # usuário expande, não a cada abertura da aba.
        self._cdi_card = card
        self._cdi_content_frame: ctk.CTkFrame | None = None
        self._cdi_expanded = False
        self._cdi_loaded = False

        self._cdi_toggle_button = ctk.CTkButton(
            card, text=self._CDI_SHOW_TEXT, fg_color=theme.INDIGO,
            command=self._toggle_cdi_section,
        )
        self._cdi_toggle_button.pack(anchor="w", padx=14, pady=(0, 14))

    def _toggle_cdi_section(self) -> None:
        self._cdi_expanded = not self._cdi_expanded
        if not self._cdi_expanded:
            self._cdi_content_frame.pack_forget()
            self._cdi_toggle_button.configure(text=self._CDI_SHOW_TEXT)
            return

        if self._cdi_content_frame is None:
            self._cdi_content_frame = ctk.CTkFrame(self._cdi_card, fg_color="transparent")

            self._cdi_value_label = ctk.CTkLabel(
                self._cdi_content_frame, text="Buscando CDI atual...",
                text_color=theme.TEXT_PRIMARY, font=ctk.CTkFont(size=12),
            )
            self._cdi_value_label.pack(anchor="w", pady=(0, 8))

            self._cdi_chart = LineChart(self._cdi_content_frame)
            self._cdi_chart.pack(anchor="w", pady=(0, 8))

            ctk.CTkButton(
                self._cdi_content_frame, text="Atualizar CDI (BCB)", fg_color=theme.INDIGO,
                command=self._fetch_cdi,
            ).pack(anchor="w", pady=(0, 8))

        self._cdi_content_frame.pack(anchor="w", padx=14, pady=(0, 14))
        self._cdi_toggle_button.configure(text=self._CDI_HIDE_TEXT)

        if not self._cdi_loaded:
            self._cdi_loaded = True
            self._fetch_cdi()

    def _fetch_cdi(self) -> None:
        # O histórico (fetch_cdi_history) busca ~3 anos de dados diários do BCB antes de
        # agregar por mês — bem mais lento que a taxa atual, e por ser uma chamada de rede
        # síncrona travava a janela inteira até responder (Tk é single-threaded, nada mais
        # processa nesse meio tempo). Roda numa thread separada; o resultado só toca em widgets
        # Tk de volta na thread principal via self.after(), que é a forma seguro de fazer isso.
        self._cdi_value_label.configure(text="Buscando...")
        threading.Thread(target=self._fetch_cdi_worker, daemon=True).start()

    def _fetch_cdi_worker(self) -> None:
        rate = market_data.fetch_current_cdi_rate()
        history = market_data.fetch_cdi_history()
        self.after(0, lambda: self._apply_cdi_result(rate, history))

    def _apply_cdi_result(self, rate, history) -> None:
        if rate is None:
            self._cdi_value_label.configure(
                text="Não foi possível buscar o CDI atual (sem internet?).",
                text_color=theme.VALUE_EXPENSE)
        else:
            self._cdi_value_label.configure(
                text=f"CDI atual: {rate.percent_per_year:.2f}% a.a. (BCB, {rate.reference_date})",
                text_color=theme.ACCENT_HIGHLIGHT)

        if history:
            self._cdi_chart.update_data(history)
