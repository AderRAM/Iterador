"""Configurações (sync, dispositivo, dados). Sync/dispositivo ainda é placeholder — ver
Guide/architecture.md > Roadmap. Importar planilha/extrato e Exportar já são de verdade — ver
Guide/decisions/0022-generic-unlabeled-investment-link.md,
Guide/decisions/0023-spreadsheet-import.md, Guide/decisions/0024-nubank-statement-import.md e
UI/iterador_ui/spreadsheet_import.py/statement_import.py/data_export.py.
"""

import random
import threading
from tkinter import filedialog

import customtkinter as ctk

from iterador_ui import (
    backend_bridge, color_profiles, custom_categories, data_export, preferences, sidebar_image,
    spreadsheet_import, theme,
)
from iterador_ui.version import APP_VERSION
from iterador_ui.widgets.color_picker_dialog import ColorPickerDialog
from iterador_ui.widgets.color_profile_dialog import ColorProfileDialog, RenameProfileDialog
from iterador_ui.widgets.confirm_dialog import ConfirmDialog
from iterador_ui.widgets.dialog_utils import open_singleton
from iterador_ui.widgets.image_picker_dialog import ImagePickerDialog
from iterador_ui.widgets.statement_review_dialog import StatementReviewDialog

_BEHAVIOR_COMMON = "Comum"
_BEHAVIOR_INVESTMENT = "Investimento"


class SettingsView(ctk.CTkFrame):
    def __init__(self, master, on_visuals_changed):
        super().__init__(master, fg_color=theme.BG_APP)
        # Chamado depois de qualquer mudança que fique "presa" em widget já construído (troca de
        # perfil de cor, ver ADR-0025; troca/remoção da imagem customizada da sidebar, ver
        # ADR-0036) — na prática é sempre `IteradorApp.rebuild_ui`.
        self._on_visuals_changed = on_visuals_changed

        # Rola a tela inteira (mesmo padrão do DashboardView) — em escala de interface alta
        # (ADR-0044) os painéis abaixo passam da altura da janela e ficam inalcançáveis sem
        # redimensionar a janela na mão.
        page_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        page_scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(
            page_scroll, text="Configurações",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
        ).pack(anchor="w", padx=24, pady=(24, 8))

        ctk.CTkLabel(
            page_scroll, text=f"Versão {APP_VERSION}", text_color=theme.TEXT_PRIMARY,
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=24)

        ctk.CTkLabel(
            page_scroll, text="Em construção — status de sync e peers conhecidos entram aqui.",
            text_color=theme.TEXT_PRIMARY,
        ).pack(anchor="w", padx=24, pady=(12, 0))

        data_frame = ctk.CTkFrame(
            page_scroll, fg_color=theme.BG_PANEL_BLUE, corner_radius=12,
            border_width=1, border_color=theme.CARBON_BLACK)
        data_frame.pack(fill="x", padx=24, pady=(20, 0))

        ctk.CTkLabel(
            data_frame, text="Dados", font=ctk.CTkFont(size=14, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
        ).pack(anchor="w", padx=16, pady=(14, 4))

        buttons_row = ctk.CTkFrame(data_frame, fg_color="transparent")
        buttons_row.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkButton(
            buttons_row, text="Importar planilha", command=self._import_spreadsheet,
            **theme.outline_button_style(),
        ).pack(side="left")
        ctk.CTkButton(
            buttons_row, text="Importar extrato", command=self._import_statement,
            **theme.outline_button_style(),
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            buttons_row, text="Exportar dados (.zip)", command=self._export_data,
            **theme.outline_button_style(),
        ).pack(side="left", padx=(8, 0))

        self._data_status_label = ctk.CTkLabel(
            data_frame, text="", text_color=theme.TEXT_PRIMARY, wraplength=520, justify="left",
            font=ctk.CTkFont(size=11))
        self._data_status_label.pack(anchor="w", padx=16, pady=(0, 14))

        # Perfis de cor (ver ADR-0025) — criar/editar/renomear/remover, e trocar qual está
        # ativo. Trocar de perfil precisa reconstruir a Sidebar/view atual pra valer sem
        # reiniciar (`on_profile_applied`, ver `IteradorApp.rebuild_ui`) — mudar só o valor de
        # `theme.BG_APP` etc. não recolore widgets já construídos sozinho.
        profiles_frame = ctk.CTkFrame(
            page_scroll, fg_color=theme.BG_PANEL_BLUE, corner_radius=12,
            border_width=1, border_color=theme.CARBON_BLACK)
        profiles_frame.pack(fill="x", padx=24, pady=(20, 0))

        ctk.CTkLabel(
            profiles_frame, text="Perfis de cor", font=ctk.CTkFont(size=14, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
        ).pack(anchor="w", padx=16, pady=(14, 4))

        selector_row = ctk.CTkFrame(profiles_frame, fg_color="transparent")
        selector_row.pack(fill="x", padx=16, pady=(0, 8))
        self._profile_var = ctk.StringVar(value=color_profiles.get_active_profile_name())
        # `CTkOptionMenu` não tem `border_width`/`border_color` nativo (diferente de
        # CTkButton/CTkEntry) — a borda preta pedida entra via um `CTkFrame` fino ao redor,
        # `corner_radius` igual ao padrão do próprio menu (6) pra a borda acompanhar o contorno
        # arredondado sem sobrar quina reta. `text_color`/`dropdown_text_color` explícitos —
        # sem eles caem no cinza padrão do CTk, pouca visibilidade contra `BG_SURFACE`.
        profile_menu_border = ctk.CTkFrame(
            selector_row, fg_color="transparent", corner_radius=6,
            border_width=1, border_color=theme.CARBON_BLACK)
        profile_menu_border.pack(side="left")
        self._profile_menu = ctk.CTkOptionMenu(
            profile_menu_border, values=color_profiles.list_profiles(), variable=self._profile_var,
            fg_color=theme.BG_SURFACE, button_color=theme.INDIGO,
            text_color=theme.TEXT_PRIMARY, dropdown_text_color=theme.TEXT_PRIMARY)
        self._profile_menu.pack(padx=1, pady=1)
        ctk.CTkButton(
            selector_row, text="Aplicar", command=self._apply_profile,
            **theme.outline_button_style(strong_border=True),
        ).pack(side="left", padx=(8, 0))

        # strong_border=True nesses 5 botões (ver ADR-0029): a borda de destaque azul (padrão em
        # outline_button_style) ficava com pouca visibilidade contra o fundo BG_PANEL_BLUE deste
        # painel no modo claro (relato do usuário) — reforço neutro preto/quase-branco + negrito
        # em vez da cor de destaque.
        profile_buttons_row = ctk.CTkFrame(profiles_frame, fg_color="transparent")
        profile_buttons_row.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkButton(
            profile_buttons_row, text="Novo perfil", command=self._new_profile,
            **theme.outline_button_style(strong_border=True),
        ).pack(side="left")
        ctk.CTkButton(
            profile_buttons_row, text="Editar", command=self._edit_profile,
            **theme.outline_button_style(strong_border=True),
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            profile_buttons_row, text="Renomear", command=self._rename_profile,
            **theme.outline_button_style(strong_border=True),
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            profile_buttons_row, text="Remover", command=self._delete_profile,
            **theme.outline_button_style(strong_border=True),
        ).pack(side="left", padx=(8, 0))

        self._profile_status_label = ctk.CTkLabel(
            profiles_frame, text="", text_color=theme.TEXT_PRIMARY, wraplength=520,
            justify="left", font=ctk.CTkFont(size=11))
        self._profile_status_label.pack(anchor="w", padx=16, pady=(0, 14))

        # Imagem customizada da sidebar (ver ADR-0036) — substitui o mosaico "Iterador" por uma
        # foto do usuário, ajustada e emoldurada em `sidebar_image.set_custom_logo`. Mesmo
        # motivo de `on_visuals_changed` que "Perfis de cor" acima: o widget já construído não
        # se atualiza sozinho, precisa reconstruir a Sidebar.
        image_frame = ctk.CTkFrame(
            page_scroll, fg_color=theme.BG_PANEL_BLUE, corner_radius=12,
            border_width=1, border_color=theme.CARBON_BLACK)
        image_frame.pack(fill="x", padx=24, pady=(20, 0))

        ctk.CTkLabel(
            image_frame, text="Imagem da barra lateral", font=ctk.CTkFont(size=14, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
        ).pack(anchor="w", padx=16, pady=(14, 4))

        image_buttons_row = ctk.CTkFrame(image_frame, fg_color="transparent")
        image_buttons_row.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkButton(
            image_buttons_row, text="Escolher imagem...", command=self._choose_sidebar_image,
            **theme.outline_button_style(),
        ).pack(side="left")
        self._remove_image_button = ctk.CTkButton(
            image_buttons_row, text="Remover imagem", command=self._remove_sidebar_image,
            **theme.outline_button_style(),
        )
        self._remove_image_button.pack(side="left", padx=(8, 0))

        self._image_status_label = ctk.CTkLabel(
            image_frame, text="", text_color=theme.TEXT_PRIMARY, wraplength=520, justify="left",
            font=ctk.CTkFont(size=11))
        self._image_status_label.pack(anchor="w", padx=16, pady=(0, 14))
        self._refresh_sidebar_image_status()

        # Escala da interface (ver ADR-0044) — "letras maiores"/"tudo maior", pedido pelo
        # usuário, mesmo conceito de escala única do Blender/AutoCAD/navegadores.
        # `ctk.set_widget_scaling()` já reescala todo widget construído sozinho, ao vivo — não
        # precisa de `on_visuals_changed`/reconstruir nada (diferente de perfil de cor/imagem).
        interface_frame = ctk.CTkFrame(
            page_scroll, fg_color=theme.BG_PANEL_BLUE, corner_radius=12,
            border_width=1, border_color=theme.CARBON_BLACK)
        interface_frame.pack(fill="x", padx=24, pady=(20, 0))

        ctk.CTkLabel(
            interface_frame, text="Interface", font=ctk.CTkFont(size=14, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
        ).pack(anchor="w", padx=16, pady=(14, 4))

        ctk.CTkLabel(
            interface_frame, text="Tamanho de tudo (letras, botões, ícones) — deixa a tela mais "
                                   "cheia de detalhe ou mais fácil de ler, sem mudar o que cabe "
                                   "na janela.",
            text_color=theme.TEXT_PRIMARY, wraplength=520, justify="left",
            font=ctk.CTkFont(size=11),
        ).pack(anchor="w", padx=16, pady=(0, 8))

        self._scale_var = ctk.StringVar(value=self._scale_label(preferences.load_ui_scale()))
        ctk.CTkSegmentedButton(
            interface_frame,
            values=[self._scale_label(s) for s in theme.UI_SCALE_OPTIONS],
            variable=self._scale_var, command=self._apply_ui_scale,
            # Texto preto (não o branco padrão do CTk) — INDIGO é bem saturado, texto branco
            # fica com pouca visibilidade em cima dele; ACCENT_EXPENSE (laranja, ver botão
            # Despesa/Receita abaixo) continua com o texto branco padrão.
            # INDIGO/CARBON_BLACK são papéis "fixos" (ver theme.py) — iguais em qualquer perfil
            # de cor, então isso não muda entre perfis.
            selected_color=theme.INDIGO, text_color=theme.CARBON_BLACK,
        ).pack(anchor="w", padx=16, pady=(0, 14))

        # Categorias personalizadas (ver ADR-0028) — além das 5 fixas (Essencial/Lazer/
        # Investimento/Ativa/Passiva, sempre presentes, não aparecem nesta lista/não são
        # removíveis). "Comportamento" decide se a categoria nova entra em
        # `backend_bridge.investment_linked_categories()` (mostra seletor de investimento e
        # ajusta o valor dele, como Investimento/Passiva) ou fica só como rótulo comum (como
        # Essencial/Lazer/Ativa). Não precisa de callback tipo `on_profile_applied` — o
        # formulário de lançamento e o gráfico de consumo já leem essas listas do zero toda vez
        # que abrem/atualizam, sem cache.
        categories_frame = ctk.CTkFrame(
            page_scroll, fg_color=theme.BG_PANEL_BLUE, corner_radius=12,
            border_width=1, border_color=theme.CARBON_BLACK)
        categories_frame.pack(fill="x", padx=24, pady=(20, 0))

        ctk.CTkLabel(
            categories_frame, text="Categorias", font=ctk.CTkFont(size=14, weight="bold"),
            text_color=theme.TEXT_PRIMARY,
        ).pack(anchor="w", padx=16, pady=(14, 4))

        form_row = ctk.CTkFrame(categories_frame, fg_color="transparent")
        form_row.pack(fill="x", padx=16, pady=(0, 4))
        self._new_category_entry = ctk.CTkEntry(form_row, placeholder_text="Nome da categoria")
        self._new_category_entry.pack(side="left")
        self._new_category_type_var = ctk.StringVar(value=custom_categories.TYPES[0])
        ctk.CTkSegmentedButton(
            form_row, values=list(custom_categories.TYPES), variable=self._new_category_type_var,
            selected_color=theme.ACCENT_EXPENSE,
        ).pack(side="left", padx=(8, 0))
        self._new_category_behavior_var = ctk.StringVar(value=_BEHAVIOR_COMMON)
        ctk.CTkSegmentedButton(
            form_row, values=[_BEHAVIOR_COMMON, _BEHAVIOR_INVESTMENT],
            variable=self._new_category_behavior_var,
            # Texto preto — mesmo motivo do seletor de escala acima (INDIGO com texto branco
            # tem pouca visibilidade).
            selected_color=theme.INDIGO, text_color=theme.CARBON_BLACK,
        ).pack(side="left", padx=(8, 0))
        # Cor aleatória por padrão (ver ADR-0030) — o usuário pode trocar clicando na amostra
        # antes de criar; `_new_category_color` é o valor de verdade, o botão só reflete ele.
        self._new_category_color = random.choice(theme._AUTO_CATEGORY_PALETTE)
        self._new_category_color_button = ctk.CTkButton(
            form_row, text="", width=28, height=28, fg_color=self._new_category_color,
            border_width=1, border_color=theme.TEXT_PRIMARY,
            command=self._pick_new_category_color)
        self._new_category_color_button.pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            form_row, text="Criar categoria", command=self._create_category,
            **theme.outline_button_style(),
        ).pack(side="left", padx=(8, 0))

        self._category_status_label = ctk.CTkLabel(
            categories_frame, text="", text_color=theme.TEXT_PRIMARY, wraplength=520,
            justify="left", font=ctk.CTkFont(size=11))
        self._category_status_label.pack(anchor="w", padx=16, pady=(0, 4))

        self._category_list_frame = ctk.CTkFrame(categories_frame, fg_color="transparent")
        self._category_list_frame.pack(fill="x", padx=16, pady=(0, 14))
        self._refresh_category_list()

    def _import_spreadsheet(self) -> None:
        path = filedialog.askopenfilename(
            title="Escolher arquivo de importação",
            filetypes=[("Arquivos de Dados", "*.xlsx;*.csv"), ("Planilha Excel", "*.xlsx"), ("CSV", "*.csv"), ("Todos os arquivos", "*.*")])
        if not path:
            return
        self._data_status_label.configure(
            text="Lendo e importando — pode levar alguns segundos...",
            text_color=theme.TEXT_PRIMARY)
        # Numa thread separada — importar ~700 lançamentos de uma vez travaria a janela inteira
        # se rodasse direto no loop principal (mesmo motivo do fetch do CDI na Wiki).
        threading.Thread(target=self._import_worker, args=(path,), daemon=True).start()

    def _import_worker(self, path: str) -> None:
        try:
            # Detectar tipo de arquivo pela extensão
            if path.lower().endswith('.csv'):
                # Importar como extrato bancário (CSV)
                from iterador_ui.statement_import import parse_statement
                result = parse_statement(path)
                # Converter ParsedStatementRow para ParsedTransaction-like structure
                # ou adaptar o resto do fluxo
                # Por enquanto, usar o resultado do CSV diretamente
                existing_transactions = backend_bridge.list_transactions()
                
                # Verificar conflitos/duplicatas para CSV
                existing_keys = {
                    (t.occurred_at, t.description, t.amount.cents)
                    for t in existing_transactions}
                enums = backend_bridge.transaction_enums()
                created = 0
                skipped = 0
                for row in result.rows:
                    key = (row.occurred_at, row.description, row.amount_cents)
                    if key in existing_keys:
                        skipped += 1
                        continue
                    type_ = enums["expense"]  # CSV geralmente são despesas
                    status = enums["pending"]
                    backend_bridge.create_transaction(
                        row.description, "Essencial", type_, row.amount_cents, "BRL",
                        status, row.occurred_at, "")
                    created += 1
                
                total_parsed = len(result.rows)
                msg = (f"{created} lançamento(es) importado(s) do CSV, "
                       f"{skipped} pulado(s) (já existiam) de {total_parsed} linhas.")
                self.after(0, lambda: self._data_status_label.configure(
                    text=msg, text_color=theme.TEXT_PRIMARY))
                
                # Mostrar summary
                from iterador_ui.widgets.confirm_dialog import ConfirmDialog
                ConfirmDialog(self, "Importação CSV",
                              f"Importado {created} lançamentos do extrato CSV.\n"
                              f"{skipped} já existed. {total_parsed - created - skipped} sem categoria.",
                              on_confirm=lambda: None)
                return
            else:
                # Importar como planilha Excel (original)
                result = spreadsheet_import.parse_workbook(path)
        except Exception as exc:  # arquivo corrompido/formato inesperado — nunca travar a UI
            message = str(exc)
            self.after(0, lambda: self._data_status_label.configure(
                text=f"Falha ao ler o arquivo: {message}", text_color=theme.VALUE_EXPENSE))
            return

        # Detecção de conflitos: verifica se transações com mesma data+descrição
        # já existem no banco com valores diferentes
        existing_transactions = backend_bridge.list_transactions()
        conflicts = spreadsheet_import.detect_conflicts(result.transactions, existing_transactions)

        # Categorizar os resultados
        has_conflicts = any(c["conflict"] for c in conflicts)
        has_duplicates = any(c.get("is_duplicate_value_match", False) for c in conflicts)
        no_conflicts_no_dupes = not has_conflicts and not has_duplicates

        if no_conflicts_no_dupes:
            # Caso padrão: nada em conflito, pode importar tudo normalmente
            existing_keys = {
                (t.occurred_at, t.description, t.amount.cents)
                for t in existing_transactions}
            enums = backend_bridge.transaction_enums()
            created = 0
            skipped_duplicates = 0
            for parsed in result.transactions:
                key = (parsed.occurred_at, parsed.description, parsed.amount_cents)
                if key in existing_keys:
                    skipped_duplicates += 1
                    continue
                type_ = enums["income"] if parsed.is_income else enums["expense"]
                status = enums["paid"] if parsed.is_paid else enums["pending"]
                backend_bridge.create_transaction(
                    parsed.description, parsed.category_name, type_, parsed.amount_cents, "BRL",
                    status, parsed.occurred_at, "")
                existing_keys.add(key)
                created += 1
            self.after(0, lambda: self._show_import_summary(created, skipped_duplicates, result))
        elif has_duplicates and not has_conflicts:
            # Apenas duplicatas (mesmo valor já existe) - importar o que é novo
            existing_keys = {
                (t.occurred_at, t.description, t.amount.cents)
                for t in existing_transactions}
            enums = backend_bridge.transaction_enums()
            created = 0
            skipped = 0
            for parsed in result.transactions:
                key = (parsed.occurred_at, parsed.description, parsed.amount_cents)
                if key in existing_keys:
                    skipped += 1
                    continue
                type_ = enums["income"] if parsed.is_income else enums["expense"]
                status = enums["paid"] if parsed.is_paid else enums["pending"]
                backend_bridge.create_transaction(
                    parsed.description, parsed.category_name, type_, parsed.amount_cents, "BRL",
                    status, parsed.occurred_at, "")
                existing_keys.add(key)
                created += 1
            # Apresentar resumo considerando as duplicatas encontradas
            total_parsed = len(result.transactions)
            self.after(0, lambda: self._show_import_summary(
                created, skipped, result, has_duplicates=True))
        else:
            # Há conflitos de valor: precisamos perguntar ao usuário
            # Apresentar um diálogo com as opções
            from iterador_ui.widgets.confirm_dialog import ConfirmDialog
            from itertools import groupby

            # Agrupar conflitos por chave (data+descrição)
            conflict_groups = []
            for c in conflicts:
                if c["conflict"]:
                    group_found = False
                    for g in conflict_groups:
                        if g["key"] == c["key"]:
                            g["conflicts"].append(c)
                            group_found = True
                            break
                    if not group_found:
                        conflict_groups.append({
                            "key": c["key"],
                            "parsed": c["parsed"],
                            "existing": c["existing"],
                            "existing_values": c.get("existing_values", {}),
                            "conflicts": [c],
                        })

            # Para cada grupo de conflito, mostrar uma confirmação
            # Por enquanto, importar tudo e deixar o usuário decidir manualmente
            # ou usar o valor do existente
            # TODO: Implementar diálogo de seleção de valor por conflito

            # Por ora, importar apenas os que não têm conflito e pular os conflitos
            existing_keys = {
                (t.occurred_at, t.description, t.amount.cents)
                for t in existing_transactions}
            enums = backend_bridge.transaction_enums()
            created = 0
            skipped_conflicts = 0
            skipped_duplicates = 0
            
            for parsed in result.transactions:
                key = (parsed.occurred_at, parsed.description, parsed.amount_cents)
                # Verificar se tem conflito
                conflict_for_key = [c for c in conflicts if c["key"] == key and c["conflict"]]
                if conflict_for_key:
                    # Há conflito - pular esta transação e avisar o usuário
                    skipped_conflicts += 1
                    continue
                if key in existing_keys:
                    skipped_duplicates += 1
                    continue
                type_ = enums["income"] if parsed.is_income else enums["expense"]
                status = enums["paid"] if parsed.is_paid else enums["pending"]
                backend_bridge.create_transaction(
                    parsed.description, parsed.category_name, type_, parsed.amount_cents, "BRL",
                    status, parsed.occurred_at, "")
                existing_keys.add(key)
                created += 1

            # Mostrar resumo detalhado
            total_parsed = len(result.transactions)
            msg = (f"{created} lançamento(es) importado(s), "
                   f"{skipped_duplicates} pulado(s) (já existiam), "
                   f"{skipped_conflicts} pulado(s) (conflito de valor - usuário decisão necessária).")
            self.after(0, lambda: self._data_status_label.configure(
                text=msg, text_color=theme.TEXT_PRIMARY))

        # Atualizar label de status com informações sobre conflitos
        if has_conflicts:
            conflict_msg = f"Foram detectados {len(conflicts)} conflito(s) de valor durante a importação. "
            if has_duplicates:
                conflict_msg += f"{sum(1 for c in conflicts if c.get('is_duplicate_value_match', False))} duplicata(s) também encontrada(s). "
            conflict_msg += "Valores existentes mantidos e transações com conflitos de valor foram puladas."
            self.after(0, lambda: self._data_status_label.configure(
                text=conflict_msg, text_color=theme.VALUE_EXPENSE))
    def _show_import_summary(self, created: int, skipped_duplicates: int, result) -> None:
        text = f"{created} lançamento(s) importado(s), {skipped_duplicates} pulado(s) (já existiam)."
        if result.skipped_sheets:
            text += f" Abas ignoradas (formato incompatível): {', '.join(result.skipped_sheets)}."
        if result.warnings:
            text += f" {len(result.warnings)} aviso(s) de leitura (datas/linhas ambíguas)."
        self._data_status_label.configure(text=text, text_color=theme.TEXT_PRIMARY)

    def _import_statement(self) -> None:
        path = filedialog.askopenfilename(
            title="Escolher extrato ou planilha",
            filetypes=[("Arquivos de Dados", "*.xlsx;*.csv"), ("CSV", "*.csv"), ("Planilha Excel", "*.xlsx"), ("Todos os arquivos", "*.*")])
        if not path:
            return
        open_singleton(self, "_statement_dialog", lambda: StatementReviewDialog(
            self, path, on_created=lambda _t: None))

    def _export_data(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Exportar dados", defaultextension=".zip",
            filetypes=[("Arquivo compactado", "*.zip")])
        if not path:
            return
        try:
            data_export.export_to_zip(path)
        except OSError as exc:
            self._data_status_label.configure(
                text=f"Falha ao exportar: {exc}", text_color=theme.VALUE_EXPENSE)
            return
        self._data_status_label.configure(
            text=f"Dados exportados para {path}.", text_color=theme.TEXT_PRIMARY)

    def _refresh_sidebar_image_status(self) -> None:
        has_custom = sidebar_image.get_logo_path() is not None
        self._remove_image_button.configure(state="normal" if has_custom else "disabled")
        if has_custom:
            status_text = "Usando imagem personalizada."
        elif sidebar_image.has_bundled_default():
            status_text = "Usando a imagem padrão do Iterador."
        else:
            status_text = "Usando o logo padrão (mosaico \"Iterador\")."
        self._image_status_label.configure(text=status_text, text_color=theme.TEXT_PRIMARY)

    def _choose_sidebar_image(self) -> None:
        open_singleton(self, "_image_picker_dialog", lambda: ImagePickerDialog(
            self, on_pick=self._apply_chosen_sidebar_image, title="Escolher imagem"))

    def _apply_chosen_sidebar_image(self, path: str) -> None:
        try:
            sidebar_image.set_custom_logo(path)
        except sidebar_image.SidebarImageError as exc:
            self._image_status_label.configure(text=str(exc), text_color=theme.VALUE_EXPENSE)
            return
        self._on_visuals_changed()  # reconstrói Sidebar — este SettingsView some daqui

    def _remove_sidebar_image(self) -> None:
        sidebar_image.remove_custom_logo()
        self._on_visuals_changed()  # reconstrói Sidebar — este SettingsView some daqui

    @staticmethod
    def _scale_label(scale: float) -> str:
        return f"{round(scale * 100)}%"

    def _apply_ui_scale(self, label: str) -> None:
        scale = theme.UI_SCALE_OPTIONS[
            [self._scale_label(s) for s in theme.UI_SCALE_OPTIONS].index(label)]
        ctk.set_widget_scaling(scale)
        preferences.save_ui_scale(scale)
        # CTk já reescala todo widget construído sozinho (ver ADR-0044), mas a Sidebar tem a
        # largura travada em pixels fixos desde a construção (`pack_propagate(False)`, ver
        # ADR-0040) — só fica do tamanho novo se for reconstruída também, senão o texto dos
        # itens de navegação corta até reiniciar o app.
        self._on_visuals_changed()  # reconstrói Sidebar/view — este SettingsView some daqui

    def _refresh_profile_menu(self, select: str | None = None) -> None:
        names = color_profiles.list_profiles()
        self._profile_menu.configure(values=names)
        active = select or color_profiles.get_active_profile_name()
        if active in names:
            self._profile_var.set(active)

    def _apply_profile(self) -> None:
        name = self._profile_var.get()
        color_profiles.set_active_profile(name)
        theme.apply_profile(name)
        self._on_visuals_changed()  # reconstrói Sidebar/view — este SettingsView some daqui

    def _new_profile(self) -> None:
        open_singleton(self, "_profile_dialog", lambda: ColorProfileDialog(
            self, on_saved=self._on_profile_saved))

    def _edit_profile(self) -> None:
        name = self._profile_var.get()
        profile = color_profiles.get_profile(name)
        if profile.get("mode") != "simple":
            self._profile_status_label.configure(
                text=f'Perfil "{name}" não é editável (só perfis criados manualmente são) — '
                     "dá pra renomear ou remover.",
                text_color=theme.VALUE_EXPENSE)
            return
        open_singleton(self, "_profile_dialog", lambda: ColorProfileDialog(
            self, on_saved=self._on_profile_saved, profile_name=name))

    def _on_profile_saved(self, name: str) -> None:
        self._refresh_profile_menu(select=name)
        self._profile_status_label.configure(
            text=f'Perfil "{name}" salvo. Clique "Aplicar" pra usar ele.',
            text_color=theme.TEXT_PRIMARY)

    def _rename_profile(self) -> None:
        name = self._profile_var.get()
        open_singleton(self, "_profile_dialog", lambda: RenameProfileDialog(
            self, profile_name=name, on_renamed=self._on_profile_renamed))

    def _on_profile_renamed(self, old_name: str, new_name: str) -> None:
        self._refresh_profile_menu(select=new_name)
        self._profile_status_label.configure(
            text=f'Perfil "{old_name}" renomeado pra "{new_name}".', text_color=theme.TEXT_PRIMARY)
        if color_profiles.get_active_profile_name() == new_name:
            theme.apply_profile(new_name)

    def _delete_profile(self) -> None:
        name = self._profile_var.get()
        open_singleton(self, "_confirm_dialog", lambda: ConfirmDialog(
            self, title="Remover perfil",
            message=f'Remover o perfil "{name}"? Essa ação não pode ser desfeita.',
            confirm_text="Remover", on_confirm=lambda: self._do_delete_profile(name)))

    def _do_delete_profile(self, name: str) -> None:
        was_active = color_profiles.get_active_profile_name() == name
        try:
            color_profiles.delete_profile(name)
        except color_profiles.ProfileError as exc:
            self._profile_status_label.configure(text=str(exc), text_color=theme.VALUE_EXPENSE)
            return
        self._refresh_profile_menu()
        self._profile_status_label.configure(
            text=f'Perfil "{name}" removido.', text_color=theme.TEXT_PRIMARY)
        if was_active:
            # O perfil ativo mudou sozinho (color_profiles.delete_profile já escolheu outro) —
            # aplica e reconstrói a UI pra refletir isso na hora.
            theme.apply_profile()
            self._on_visuals_changed()

    def _pick_new_category_color(self) -> None:
        open_singleton(self, "_color_picker_dialog", lambda: ColorPickerDialog(
            self, initial_color=self._new_category_color, on_pick=self._apply_new_category_color))

    def _apply_new_category_color(self, hex_color: str) -> None:
        self._new_category_color = hex_color
        self._new_category_color_button.configure(fg_color=hex_color)

    def _create_category(self) -> None:
        name = self._new_category_entry.get()
        type_ = self._new_category_type_var.get()
        investment_linked = self._new_category_behavior_var.get() == _BEHAVIOR_INVESTMENT
        try:
            custom_categories.add_custom_category(
                name, type_, investment_linked, backend_bridge.fixed_category_names(),
                self._new_category_color)
        except custom_categories.CategoryError as exc:
            self._category_status_label.configure(text=str(exc), text_color=theme.VALUE_EXPENSE)
            return
        self._new_category_entry.delete(0, "end")
        # Nova cor aleatória pra próxima categoria — se não sorteasse de novo, a próxima viria
        # com a MESMA cor que acabou de ser usada, parecendo que "esqueceu" de aleatorizar.
        self._new_category_color = random.choice(theme._AUTO_CATEGORY_PALETTE)
        self._new_category_color_button.configure(fg_color=self._new_category_color)
        self._refresh_category_list()
        self._category_status_label.configure(
            text=f'Categoria "{name.strip()}" criada.', text_color=theme.TEXT_PRIMARY)

    def _refresh_category_list(self) -> None:
        for child in self._category_list_frame.winfo_children():
            child.destroy()

        categories = custom_categories.list_custom_categories()
        if not categories:
            ctk.CTkLabel(
                self._category_list_frame, text="Nenhuma categoria personalizada ainda.",
                text_color=theme.TEXT_PRIMARY, font=ctk.CTkFont(size=11),
            ).pack(anchor="w")
            return

        for category in categories:
            behavior = _BEHAVIOR_INVESTMENT if category["investment_linked"] else _BEHAVIOR_COMMON
            # `.get("color")` (nunca `category["color"]`) — categorias criadas antes da ADR-0030
            # (cor editável) não têm esse campo gravado; cai no mesmo hash determinístico que
            # `theme.category_color()` já usa como último recurso, em vez de KeyError.
            color = category.get("color") or theme.category_color(category["name"])
            row = ctk.CTkFrame(self._category_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkButton(
                row, text="", width=22, height=22, fg_color=color,
                border_width=1, border_color=theme.TEXT_PRIMARY,
                command=lambda n=category["name"], c=color: self._edit_category_color(n, c),
            ).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(
                row, text=f'{category["name"]} — {category["type"]}/{behavior}',
                text_color=theme.TEXT_PRIMARY, font=ctk.CTkFont(size=11),
            ).pack(side="left")
            ctk.CTkButton(
                row, text="Remover", width=64, command=lambda n=category["name"]: self._delete_category(n),
                **theme.outline_button_style(),
            ).pack(side="right")

    def _edit_category_color(self, name: str, current_color: str) -> None:
        open_singleton(self, "_color_picker_dialog", lambda: ColorPickerDialog(
            self, initial_color=current_color,
            on_pick=lambda hex_color: self._apply_category_color(name, hex_color)))

    def _apply_category_color(self, name: str, hex_color: str) -> None:
        custom_categories.update_custom_category_color(name, hex_color)
        self._refresh_category_list()

    def _delete_category(self, name: str) -> None:
        open_singleton(self, "_confirm_dialog", lambda: ConfirmDialog(
            self, title="Remover categoria",
            message=f'Remover a categoria "{name}"? Lançamentos que já usam ela continuam '
                    "mostrando o nome normalmente, só some das opções pra lançamentos novos.",
            confirm_text="Remover", on_confirm=lambda: self._do_delete_category(name)))

    def _do_delete_category(self, name: str) -> None:
        custom_categories.remove_custom_category(name)
        self._refresh_category_list()
        self._category_status_label.configure(
            text=f'Categoria "{name}" removida.', text_color=theme.TEXT_PRIMARY)
