from __future__ import annotations

from pathlib import Path
import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox, ttk
from weakref import WeakKeyDictionary

from input_parser import ParsedInput, format_cpf, normalize_cpf, normalize_plate, parse_validation_text
from report_queries import index_results, lookup_detected_data
from report_store import ReportError, ReportStore
from validation_core import (
    SELECT, ValidationInputError, copy_text_to_clipboard,
    generate_amazon_validation, generate_meli_validation,
)


APP_TITLE = "Validador de Cadastro"
BASE_DIR = Path(__file__).resolve().parent
BG = "#f0f0f0"
RED = "#c62828"
GREEN = "#16803c"
AMBER = "#d97706"
STATUS_OPTIONS = (SELECT, "OK", "Renovar", "Em análise", "Inapto", "Vencido", "Sem cadastro", "Pesquisa concluída", "Repesquisa")
STANDARD_OPTIONS = (SELECT, "OK", "Renovar", "Inapto")
CHECKLIST_OPTIONS = (SELECT, "OK", "Vencido", "Sem checklist", "Inapto", "Reprovado")
REGISTRATION_OPTIONS = (SELECT, "Cadastro", "Validar", "Atualizar cadastro", "Sem cadastro")
MELI_ITEM_OPTIONS = (SELECT, "OK", "Renovar", "Inapto", "Sem cadastro", "Em análise")
MELI_FLEET_OPTIONS = (SELECT, "OK", "Sem cadastro")
MELI_CHECK_OPTIONS = (SELECT, "OK", "Vencido", "Sem checklist")


class ReportImporterApp:
    """Validador clássico com consultas locais aos relatórios carregados em memória."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.store = ReportStore()
        self.paths = {"motorista": tk.StringVar(), "veiculo": tk.StringVar()}
        self.status_widgets: dict[str, tk.Label] = {}
        self.parsed = ParsedInput()
        self.lookup_results: list[dict] = []
        self.result_map: dict = {}
        self.operation = tk.StringVar(value="AMAZON")
        self.amazon_vars: dict[str, tk.StringVar] = {}
        self.amazon_combos: dict[str, ttk.Combobox] = {}
        self.fleet_vars: dict[str, tk.StringVar] = {}
        self.lweb_vars: dict[str, tk.StringVar] = {}
        self.meli_vars: dict[tuple[str, str], tk.StringVar] = {}
        self.meli_section_frames: dict[str, ttk.LabelFrame] = {}
        self.meli_use_vecfleet = tk.BooleanVar(value=True)
        self.fleet_apta = tk.BooleanVar(value=False)
        self.possui_carreta = tk.BooleanVar(value=True)
        self.year_var = tk.StringVar()
        self.minimum_year = tk.StringVar(value="2013")
        self.vehicle_role_vars: dict[str, tk.StringVar] = {}
        self.validity_labels: dict[tuple[str, str], tk.Label] = {}
        self.driver2_summary = tk.StringVar(value="Motorista 2 BRK: —")

        root.title(APP_TITLE)
        root.geometry("1100x980")
        root.minsize(620, 460)
        root.configure(bg=BG)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._responsive_fonts = WeakKeyDictionary()
        self._responsive_spacing = WeakKeyDictionary()
        self._resize_job = None
        self._current_scale = 1.0
        self._build_responsive_container()
        self._build_header()
        self._build_import_area()
        self._build_input_area()
        self._build_identity_area()
        self.amazon_panel = tk.Frame(self.content, bg=BG)
        self._build_status_area()
        self._build_fleet_area()
        self._build_lweb_area()
        self.fleet_trailer_widgets = self.fleet_fields.grid_slaves(row=2)
        self.lweb_trailer_widgets = self.lweb_area.grid_slaves(row=2)
        self._fleet_apta_changed()
        self._build_meli_area()
        self._build_actions_and_preview()
        self._bind_shortcuts()
        self._refresh_vehicle_dependent_controls()
        self._operation_changed()
        root.bind("<Configure>", self._on_root_resize, add="+")
        self._on_root_resize()

    def _build_responsive_container(self) -> None:
        """Keep the classic vertical layout while allowing small screens to scroll."""
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(self.root, bg=BG, borderwidth=0, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vertical_scroll = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.vertical_scroll.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=self.vertical_scroll.set)
        self.content = tk.Frame(self.canvas, bg=BG)
        self.content_window = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", self._content_resized)
        self.canvas.bind("<Configure>", self._canvas_resized)
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

    def _content_resized(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self._fit_content_height()

    def _canvas_resized(self, event) -> None:
        self.canvas.itemconfigure(self.content_window, width=event.width)
        self._fit_content_height()

    def _fit_content_height(self) -> None:
        if not self.content.winfo_exists():
            return
        requested = self.content.winfo_reqheight()
        available = self.canvas.winfo_height()
        target = max(requested, available)
        current = int(float(self.canvas.itemcget(self.content_window, "height") or 0))
        if current != target:
            self.canvas.itemconfigure(self.content_window, height=target)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _bind_mousewheel(self, _event=None) -> None:
        self.root.bind_all("<MouseWheel>", self._on_mousewheel, add="+")

    def _unbind_mousewheel(self, _event=None) -> None:
        self.root.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def _on_root_resize(self, _event=None) -> None:
        if self._resize_job is not None:
            try:
                self.root.after_cancel(self._resize_job)
            except tk.TclError:
                pass
        self._resize_job = self.root.after(120, self._apply_responsive_scale)

    @staticmethod
    def _scaled_spacing(value, scale):
        if isinstance(value, tuple):
            return tuple(max(0, round(float(part) * scale)) for part in value)
        try:
            return max(0, round(float(value) * scale))
        except (TypeError, ValueError):
            return value

    def _remember_responsive_widget(self, widget: tk.Widget, scale: float) -> None:
        if widget not in self._responsive_fonts:
            try:
                font = tkfont.Font(root=self.root, font=widget.cget("font"))
                base_size = abs(int(font.cget("size"))) or 9
                self._responsive_fonts[widget] = (font, base_size)
                widget.configure(font=font)
            except (tk.TclError, TypeError, ValueError):
                pass
        if widget in self._responsive_fonts:
            font, base_size = self._responsive_fonts[widget]
            minimum = 8 if base_size >= 8 else 7
            font.configure(size=max(minimum, round(base_size * scale)))

        if widget not in self._responsive_spacing:
            try:
                manager = widget.winfo_manager()
                options = widget.pack_info() if manager == "pack" else widget.grid_info() if manager == "grid" else {}
                spacing = {key: options[key] for key in ("padx", "pady", "ipadx", "ipady") if key in options}
                if spacing:
                    self._responsive_spacing[widget] = (manager, spacing)
            except tk.TclError:
                pass
        if widget in self._responsive_spacing:
            manager, spacing = self._responsive_spacing[widget]
            # grid_remove/pack_forget preserve the old layout metadata, but the
            # widget must stay hidden until the application explicitly restores it.
            if widget.winfo_manager() != manager:
                return
            scaled = {key: self._scaled_spacing(value, scale) for key, value in spacing.items()}
            try:
                widget.pack_configure(**scaled) if manager == "pack" else widget.grid_configure(**scaled)
            except tk.TclError:
                pass

    def _apply_responsive_scale(self) -> None:
        self._resize_job = None
        width = max(1, self.root.winfo_width())
        height = max(1, self.root.winfo_height())
        scale = max(0.62, min(1.16, min(width / 1100, height / 980)))
        self._current_scale = scale
        stack = [self.content]
        while stack:
            widget = stack.pop()
            self._remember_responsive_widget(widget, scale)
            try:
                stack.extend(widget.winfo_children())
            except tk.TclError:
                pass
        if self.logo_label is not None and self.logo_original is not None:
            from PIL import ImageTk
            target = (max(80, round(145 * scale)), max(28, round(50 * scale)))
            image = self.logo_original.copy()
            image.thumbnail(target)
            self.logo_image = ImageTk.PhotoImage(image)
            self.logo_label.configure(image=self.logo_image)
            self.logo_label.place_configure(x=round(-18 * scale), y=round(27 * scale))
        if self.author_label is not None:
            self.author_label.place_configure(x=round(10 * scale), y=round(7 * scale))
        self._fit_content_height()

    # --- Layout: follows the legacy Validador's header, status rows and sections. ---
    def _build_header(self) -> None:
        self.author_label = tk.Label(self.content, text="Desenvolvido por: Nixon Deam da Silva Cavalcanti", font=("Arial", 8), fg="gray40", bg=BG)
        self.author_label.place(x=10, y=7)
        self.logo_image = None
        self.logo_original = None
        self.logo_label = None
        logo_path = BASE_DIR / "losung.png"
        if logo_path.is_file():
            try:
                from PIL import Image, ImageTk
                self.logo_original = Image.open(logo_path).copy()
                self.logo_original.thumbnail((145, 50))
                self.logo_image = ImageTk.PhotoImage(self.logo_original)
                self.logo_label = tk.Label(self.content, image=self.logo_image, borderwidth=0, bg=BG)
                self.logo_label.place(relx=1, x=-18, y=27, anchor="ne")
            except Exception:
                pass
        tk.Label(self.content, text="🚛 VALIDADOR DE CADASTRO", font=("Arial", 16, "bold"), bg=BG).pack(pady=(27, 0))
        self.shortcut_label = tk.Label(self.content, text="", font=("Arial", 9, "bold"), fg="darkgreen", bg=BG)
        self.shortcut_label.pack(pady=(2, 3))
        op_row = tk.Frame(self.content, bg=BG)
        op_row.pack(pady=(0, 4))
        ttk.Radiobutton(op_row, text="AMAZON", value="AMAZON", variable=self.operation, command=self._operation_changed).pack(side="left", padx=8)
        ttk.Radiobutton(op_row, text="MELI", value="MELI", variable=self.operation, command=self._operation_changed).pack(side="left", padx=8)

    def _build_import_area(self) -> None:
        area = tk.LabelFrame(self.content, text="RELATÓRIOS BRK — IMPORTAÇÃO TEMPORÁRIA", padx=7, pady=4, font=("Arial", 9, "bold"), bg=BG)
        area.pack(fill="x", padx=14, pady=(0, 3))
        report_area = tk.Frame(area, bg=BG)
        report_area.grid(row=0, column=0, sticky="ew")
        report_area.columnconfigure(1, weight=1)
        self._report_row(report_area, 0, "motorista", "Motorista")
        self._report_row(report_area, 1, "veiculo", "Veículos")
        tk.Button(area, text="APAGAR DADOS CARREGADOS", font=("Arial", 9, "bold"), command=self.delete_loaded_data).grid(row=0, column=1, rowspan=2, sticky="ns", padx=(9, 3), pady=2)
        area.columnconfigure(0, weight=1)

    def _report_row(self, parent: tk.Widget, row: int, kind: str, label: str) -> None:
        tk.Label(parent, text=f"Relatório de Pesquisa de {label}:", font=("Arial", 9), bg=BG, width=27, anchor="w").grid(row=row, column=0, sticky="w", pady=1)
        ttk.Entry(parent, textvariable=self.paths[kind], state="readonly").grid(row=row, column=1, sticky="ew", padx=3, pady=1)
        tk.Button(parent, text="Selecionar...", command=lambda k=kind: self.select_file(k)).grid(row=row, column=2, padx=2)
        status = tk.Label(parent, text="Não carregado", fg=RED, bg=BG, anchor="w", width=31, font=("Arial", 8))
        status.grid(row=row, column=3, sticky="w", padx=3)
        self.status_widgets[kind] = status

    def _build_input_area(self) -> None:
        area = tk.LabelFrame(self.content, text="DADOS PARA IDENTIFICAÇÃO", padx=7, pady=4, font=("Arial", 9, "bold"), bg=BG)
        area.pack(fill="x", padx=14, pady=3)
        area.columnconfigure(0, weight=1)
        self.input_text = tk.Text(area, height=3, wrap="word", font=("Arial", 10))
        self.input_text.grid(row=0, column=0, sticky="ew")
        self.input_text.bind("<Control-v>", self._paste_into_input)
        self.input_text.bind("<Control-V>", self._paste_into_input)
        self.input_text.bind("<Shift-Insert>", self._paste_into_input)
        actions = tk.Frame(area, bg=BG)
        actions.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        tk.Button(actions, text="IDENTIFICAR DADOS", font=("Arial", 9, "bold"), command=self.identify_data).pack(side="left")
        self.identify_message = tk.Label(actions, text="Cole os dados recebidos e identifique os campos.", bg=BG, fg="gray35", anchor="w", wraplength=700)
        self.identify_message.pack(side="left", padx=10, fill="x", expand=True)

    def _paste_into_input(self, _event=None):
        """Handle Windows paste shortcuts explicitly in the multiline input."""
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            return "break"
        try:
            selected = self.input_text.tag_ranges("sel")
            if selected:
                self.input_text.delete(selected[0], selected[1])
            self.input_text.insert("insert", text)
        except tk.TclError:
            return "break"
        return "break"

    def _build_identity_area(self) -> None:
        self.identity_area = tk.LabelFrame(self.content, text="DADOS IDENTIFICADOS", padx=6, pady=3, font=("Arial", 9, "bold"), bg=BG)
        self.identity_area.pack(fill="x", padx=14, pady=2)
        self.identity_content = tk.Frame(self.identity_area, bg=BG)
        self.identity_content.pack(fill="x")
        self.identity_placeholder = tk.Label(self.identity_content, text="A identificação preencherá aqui motorista(s) e placa(s).", bg=BG, fg="gray40", anchor="w")
        self.identity_placeholder.pack(anchor="w")
        ttk.Checkbutton(self.identity_area, text="Possui carreta", variable=self.possui_carreta, command=self._trailer_option_changed).pack(anchor="w", pady=(2, 0))

    def _build_status_area(self) -> None:
        self.status_frame = tk.Frame(self.amazon_panel, bg=BG)
        self.status_frame.pack(fill="x", padx=17, pady=(2, 0))
        self.status_title = tk.Label(self.status_frame, text="🟢 STATUS", font=("Arial", 11, "bold"), fg="green", bg=BG, anchor="w")
        self.status_title.grid(row=0, column=0, sticky="w", pady=(3, 2))
        specs = [
            ("BRK", STATUS_OPTIONS, "driver1"),
            ("Onboarding", STANDARD_OPTIONS, None),
            ("ET", STANDARD_OPTIONS, None),
            ("TDD", STANDARD_OPTIONS, None),
            ("Checklist", CHECKLIST_OPTIONS, None),
            ("Placa Cavalo BRK", STATUS_OPTIONS, "horse"),
            ("Placa Carreta BRK", STATUS_OPTIONS, "trailer"),
        ]
        self.status_row_frames: dict[str, tk.Frame] = {}
        for row, (name, choices, key) in enumerate(specs, 1):
            line = tk.Frame(self.status_frame, bg=BG)
            line.grid(row=row, column=0, sticky="w")
            self.status_row_frames[name] = line
            tk.Label(line, text=name, bg=BG, width=22, anchor="w", font=("Arial", 9)).pack(side="left")
            var = self.amazon_vars.setdefault(name, tk.StringVar(value=SELECT))
            combo = ttk.Combobox(line, textvariable=var, values=choices, state="readonly", width=23)
            combo.pack(side="left")
            self.amazon_combos[name] = combo
            if key:
                label = tk.Label(line, text="—", fg=RED, bg=BG, width=14, anchor="w", font=("Arial", 9, "bold"))
                label.pack(side="left", padx=(13, 0))
                self.validity_labels[(key, "")] = label

        year_line = tk.Frame(self.status_frame, bg=BG)
        year_line.grid(row=8, column=0, sticky="w", pady=(0, 3))
        tk.Label(year_line, text="Ano do Cavalo", bg=BG, width=22, anchor="w", font=("Arial", 9)).pack(side="left")
        ttk.Entry(year_line, textvariable=self.year_var, width=25).pack(side="left")
        tk.Label(year_line, text="Ano mínimo", bg=BG, font=("Arial", 9)).pack(side="left", padx=(18, 5))
        ttk.Combobox(year_line, textvariable=self.minimum_year, values=tuple(str(y) for y in range(2008, 2019)), state="readonly", width=8).pack(side="left")
        tk.Label(year_line, text="(não consta nos relatórios)", bg=BG, fg="gray40", font=("Arial", 8)).pack(side="left", padx=8)

    def _build_fleet_area(self) -> None:
        self.fleet_title = tk.Label(self.amazon_panel, text="🟢 FROTA LEGAL", font=("Arial", 11, "bold"), fg="green", bg=BG, anchor="w")
        self.fleet_title.pack(fill="x", padx=17, pady=(4, 1))
        self.fleet_area = tk.Frame(self.amazon_panel, bg=BG)
        self.fleet_area.pack(fill="x", padx=17)
        ttk.Checkbutton(self.fleet_area, text="APTA", variable=self.fleet_apta, command=self._fleet_apta_changed).grid(row=0, column=1, sticky="w")
        tk.Label(self.fleet_area, text="Inspeção", bg=BG, width=22, anchor="w", font=("Arial", 9)).grid(row=0, column=0, sticky="w")
        self.fleet_fields = tk.Frame(self.fleet_area, bg=BG)
        self.fleet_fields.grid(row=1, column=0, columnspan=3, sticky="w")
        for row, name in enumerate(("Motorista", "Cavalo", "Carreta")):
            self._add_combo(self.fleet_fields, name, REGISTRATION_OPTIONS, row, self.fleet_vars, width=23)

    def _build_lweb_area(self) -> None:
        self.lweb_title = tk.Label(self.amazon_panel, text="🟢 LWEB", font=("Arial", 11, "bold"), fg="green", bg=BG, anchor="w")
        self.lweb_title.pack(fill="x", padx=17, pady=(4, 1))
        self.lweb_area = tk.Frame(self.amazon_panel, bg=BG)
        self.lweb_area.pack(fill="x", padx=17)
        for row, name in enumerate(("Motorista", "Cavalo", "Carreta")):
            self._add_combo(self.lweb_area, name, REGISTRATION_OPTIONS, row, self.lweb_vars, width=23)

    def _build_meli_area(self) -> None:
        self.meli_panel = tk.LabelFrame(self.content, text="MELI", padx=7, pady=4, font=("Arial", 9, "bold"), bg=BG)
        note = tk.Label(self.meli_panel, text="Os relatórios carregados são consultados somente para AMAZON; os campos MELI são preenchidos manualmente.", bg=BG, fg="#8a4b08", anchor="w")
        note.pack(fill="x", pady=(0, 3))
        ttk.Checkbutton(self.meli_panel, text="Validar VEC FLEET", variable=self.meli_use_vecfleet, command=self._toggle_vecfleet).pack(anchor="w")
        self.meli_content = tk.Frame(self.meli_panel, bg=BG)
        self.meli_content.pack(fill="x")
        self._refresh_meli_fields()

    def _build_actions_and_preview(self) -> None:
        self.action_row = tk.Frame(self.content, bg=BG)
        self.action_row.pack(pady=(5, 2))
        tk.Button(self.action_row, text="GERAR VALIDAÇÃO", font=("Arial", 11, "bold"), command=self.generate, width=19).pack(side="left", padx=5, ipady=3)
        tk.Button(self.action_row, text="COPIAR", font=("Arial", 11), command=self.copy_preview, width=13).pack(side="left", padx=5, ipady=3)
        tk.Button(self.action_row, text="LIMPAR", font=("Arial", 11), command=self.clear_validation, width=13).pack(side="left", padx=5, ipady=3)
        tk.Label(self.content, text="Prévia da Validação", font=("Arial", 11, "bold"), bg=BG).pack(pady=(1, 0))
        preview_frame = tk.Frame(self.content, bg=BG)
        preview_frame.pack(fill="both", expand=True, padx=58, pady=(3, 7))
        self.preview = tk.Text(preview_frame, height=8, wrap="word", font=("Consolas", 10))
        scroll = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview.yview)
        self.preview.configure(yscrollcommand=scroll.set)
        self.preview.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _add_combo(self, parent, label: str, choices, row: int, storage: dict[str, tk.StringVar], width: int = 20):
        tk.Label(parent, text=label, bg=BG, width=22, anchor="w", font=("Arial", 9)).grid(row=row, column=0, sticky="w", pady=1)
        var = storage.setdefault(label, tk.StringVar(value=SELECT))
        combo = ttk.Combobox(parent, textvariable=var, values=choices, state="readonly", width=width)
        combo.grid(row=row, column=1, sticky="w", pady=1)
        return combo

    def _bind_shortcuts(self) -> None:
        for key, callback in (("F1", self._shortcut_f1), ("F2", self._shortcut_f2), ("F3", self._shortcut_f3), ("F4", self._shortcut_f4)):
            self.root.bind(f"<{key}>", callback)

    def _update_shortcut_label(self) -> None:
        text = ("⚡ F1 = BRK/CHECKS OK    ⚡ F2 = VEC FLEET OK    ⚡ F3 = LWEB OK    ⚡ F4 = VEC FLEET SEM CADASTRO"
                if self.operation.get() == "MELI" else
                "⚡ F1 = STATUS OK    ⚡ F2 = INSPEÇÃO APTA    ⚡ F3 = LWEB OK    ⚡ F4 = FROTA CADASTRO OK")
        self.shortcut_label.config(text=text)

    def _operation_changed(self) -> None:
        self._update_shortcut_label()
        if self.operation.get() == "AMAZON":
            self.meli_panel.pack_forget()
            self.amazon_panel.pack(fill="x", before=self.action_row)
        else:
            self.amazon_panel.pack_forget()
            self.meli_panel.pack(fill="x", padx=17, pady=(5, 2), before=self.action_row)
        if self.parsed.drivers or self.parsed.vehicles:
            self._refresh_lookups()
            self._apply_lookup_results()

    def _fleet_apta_changed(self) -> None:
        if self.fleet_apta.get():
            self.fleet_fields.grid_remove()
        else:
            self.fleet_fields.grid()
        self.fleet_title.config(text=f"{'🟢' if self.fleet_apta.get() else '🔴'} FROTA LEGAL", fg=GREEN if self.fleet_apta.get() else RED)

    def _refresh_vehicle_dependent_controls(self) -> None:
        trailers = self.possui_carreta.get()
        for widget in self.fleet_trailer_widgets + self.lweb_trailer_widgets:
            if trailers:
                widget.grid()
            else:
                widget.grid_remove()
        if not trailers:
            self.fleet_vars.setdefault("Carreta", tk.StringVar(value=SELECT)).set(SELECT)
            self.lweb_vars.setdefault("Carreta", tk.StringVar(value=SELECT)).set(SELECT)
        self.status_row_frames["Placa Carreta BRK"].grid() if trailers else self.status_row_frames["Placa Carreta BRK"].grid_remove()

    def _trailer_option_changed(self) -> None:
        self._refresh_vehicle_dependent_controls()
        self._refresh_meli_fields()

    def _refresh_meli_fields(self) -> None:
        existing = {key: var.get() for key, var in self.meli_vars.items()}
        for child in self.meli_content.winfo_children():
            child.destroy()
        self.meli_vars.clear()
        self.meli_section_frames.clear()
        entities = [("Motorista" if i == 1 else f"Motorista {i}", f"driver:{i}") for i, _ in enumerate(self.parsed.drivers, 1)]
        vehicles = [v for v in self.parsed.vehicles if self.possui_carreta.get() or not v.role.startswith("Carreta")]
        entities.extend((vehicle.role or f"Placa {i}", f"vehicle:{vehicle.plate}") for i, vehicle in enumerate(vehicles, 1))
        specs = (("LWEB", entities, MELI_ITEM_OPTIONS), ("BRK", entities, MELI_ITEM_OPTIONS), ("VEC FLEET", entities, MELI_FLEET_OPTIONS), ("CHECKS", [(n, f"check:{n}") for n in ("15zenal", "Anual", "Veicular")], MELI_CHECK_OPTIONS))
        for idx, (section, items, options) in enumerate(specs):
            frame = ttk.LabelFrame(self.meli_content, text=section, padding=4)
            frame.grid(row=idx // 2, column=idx % 2, sticky="nw", padx=4, pady=3)
            self.meli_section_frames[section] = frame
            for row, (label, key) in enumerate(items):
                var = self.meli_vars[(section, key)] = tk.StringVar(value=existing.get((section, key), SELECT))
                tk.Label(frame, text=label, bg=BG, anchor="w", width=18).grid(row=row, column=0, sticky="w")
                ttk.Combobox(frame, textvariable=var, values=options, state="readonly", width=17).grid(row=row, column=1, sticky="w")
        self.meli_content.columnconfigure(0, weight=1)
        self.meli_content.columnconfigure(1, weight=1)
        self._toggle_vecfleet()

    def _toggle_vecfleet(self) -> None:
        frame = self.meli_section_frames.get("VEC FLEET")
        if frame:
            frame.grid() if self.meli_use_vecfleet.get() else frame.grid_remove()

    # --- Report loading and local-only identification. ---
    def select_file(self, kind: str) -> None:
        title = "Selecione o relatório de motorista" if kind == "motorista" else "Selecione o relatório de veículos"
        selected = filedialog.askopenfilename(parent=self.root, title=title, filetypes=[("Planilha Excel (.xlsx)", "*.xlsx")])
        if not selected:
            return
        previous = self.paths[kind].get()
        self.paths[kind].set(selected)
        if not self._load_file(kind):
            self.paths[kind].set(previous)

    def _load_file(self, kind: str) -> bool:
        try:
            report = self.store.load(kind, self.paths[kind].get())
        except ReportError as exc:
            messagebox.showerror("Relatório inválido", str(exc), parent=self.root)
            self._refresh_report_label(kind)
            return False
        time_text = report.loaded_at.strftime("%d/%m/%Y %H:%M:%S")
        self.status_widgets[kind].config(text=f"{report.record_count:,} registros | {time_text}", fg=GREEN)
        if self.parsed.drivers or self.parsed.vehicles:
            self._refresh_lookups()
            self._apply_lookup_results()
        return True

    def _refresh_report_label(self, kind: str) -> None:
        report = self.store.reports[kind]
        if report is None:
            self.status_widgets[kind].config(text="Não carregado", fg=RED)
        else:
            self.status_widgets[kind].config(text=f"{report.record_count:,} registros", fg=GREEN)

    def identify_data(self) -> None:
        parsed = parse_validation_text(self.input_text.get("1.0", "end-1c"))
        self.parsed = parsed
        if any(v.role.startswith("Carreta") for v in parsed.vehicles):
            self.possui_carreta.set(True)
        elif parsed.vehicles and all(v.role for v in parsed.vehicles):
            self.possui_carreta.set(False)
        self.vehicle_role_vars.clear()
        self._render_identity()
        self._refresh_vehicle_dependent_controls()
        self._refresh_meli_fields()
        self._refresh_lookups()
        self._apply_lookup_results()
        if not parsed.drivers and not parsed.vehicles:
            self.identify_message.config(text="Nenhum CPF ou placa válido encontrado.", fg=RED)
        else:
            note = " ".join(parsed.warnings)
            errors = [] if self.operation.get() == "MELI" else list(dict.fromkeys(item.get("error", "") for item in self.lookup_results if item.get("error")))
            lookup_note = " | ".join(errors)
            identified = f"Identificados {len(parsed.drivers)} motorista(s) e {len(parsed.vehicles)} veículo(s)."
            message = " ".join(part for part in (note, identified, lookup_note) if part)
            self.identify_message.config(text=message, fg="#8a4b08" if note or errors else GREEN)

    def _render_identity(self) -> None:
        for child in self.identity_content.winfo_children():
            child.destroy()
        self.validity_labels.pop(("driver2", ""), None)
        self.driver2_summary.set("Motorista 2 BRK: —")
        result_map = index_results(self.lookup_results)
        row = 0
        for i, driver in enumerate(self.parsed.drivers, 1):
            name = driver.name or "—"
            ttk.Label(self.identity_content, text=f"Motorista {i}:", width=13).grid(row=row, column=0, sticky="w", padx=(0, 4), pady=1)
            ttk.Label(self.identity_content, text=name, width=32).grid(row=row, column=1, sticky="w", pady=1)
            ttk.Label(self.identity_content, text="CPF:").grid(row=row, column=2, sticky="w", padx=(7, 3))
            ttk.Label(self.identity_content, text=format_cpf(driver.cpf), width=17).grid(row=row, column=3, sticky="w")
            result = result_map.get(("motorista", normalize_cpf(driver.cpf)), {})
            if i == 2:
                status = result.get("status") or "—"
                self.driver2_summary.set(f"Motorista 2 BRK: {status}")
                ttk.Label(self.identity_content, textvariable=self.driver2_summary, width=24).grid(row=row, column=4, sticky="w", padx=(10, 0))
                self._create_validity_label(self.identity_content, row, 5, ("driver2", ""), result)
            row += 1
        for i, vehicle in enumerate(self.parsed.vehicles, 1):
            ttk.Label(self.identity_content, text=f"Placa {i}:", width=13).grid(row=row, column=0, sticky="w", padx=(0, 4), pady=1)
            role_var = tk.StringVar(value=vehicle.role or "Não definido")
            self.vehicle_role_vars[normalize_plate(vehicle.plate)] = role_var
            role_combo = ttk.Combobox(self.identity_content, textvariable=role_var, values=("Não definido", "Cavalo", "Carreta 1", "Carreta 2"), state="readonly", width=13)
            role_combo.grid(row=row, column=1, sticky="w")
            role_combo.bind("<<ComboboxSelected>>", lambda _e, item=vehicle, var=role_var: self._role_changed(item, var))
            ttk.Label(self.identity_content, text="Placa:").grid(row=row, column=2, sticky="w", padx=(7, 3))
            ttk.Label(self.identity_content, text=vehicle.plate, width=12).grid(row=row, column=3, sticky="w")
            row += 1
        if not row:
            tk.Label(self.identity_content, text="A identificação preencherá aqui motorista(s) e placa(s).", bg=BG, fg="gray40", anchor="w").grid(row=0, column=0, sticky="w")
        for col in range(5):
            self.identity_content.columnconfigure(col, weight=1 if col == 1 else 0)
        self._refresh_vehicle_dependent_controls()
        self._apply_lookup_results(update_identity=False)

    def _role_changed(self, vehicle, variable) -> None:
        role = variable.get()
        vehicle.role = "" if role == "Não definido" else role
        if any(other is not vehicle and other.role == "Cavalo" for other in self.parsed.vehicles) and role == "Cavalo":
            messagebox.showerror("Papel duplicado", "Já existe uma placa definida como Cavalo.", parent=self.root)
            vehicle.role = ""
            variable.set("Não definido")
        self._refresh_vehicle_dependent_controls()
        self._refresh_meli_fields()
        self._apply_lookup_results()

    def _refresh_lookups(self) -> None:
        self.lookup_results = lookup_detected_data(self.store, self.parsed, self.operation.get())
        self.result_map = index_results(self.lookup_results)

    def _create_validity_label(self, parent, row: int, column: int, key: tuple[str, str], result: dict) -> None:
        label = tk.Label(parent, text="—", bg=BG, fg=RED, font=("Arial", 9, "bold"), anchor="w")
        label.grid(row=row, column=column, sticky="w", padx=(10, 0))
        self.validity_labels[key] = label
        self._set_validity_label(label, result.get("validity"), result.get("status_brk"), result.get("status"))

    @staticmethod
    def _set_validity_label(label: tk.Label, value: str | None, status_brk: str | None = None, status: str | None = None) -> None:
        raw = (status_brk or "").strip().casefold()
        normalized = (status or "").strip().casefold()
        validity = (value or "").strip()
        if raw in ("vencida", "vencido") or normalized in ("vencida", "vencido"):
            label.config(text="VENCIDO", fg=RED)
        elif raw in ("enviar renovação", "enviar renovacao") or normalized == "renovar":
            label.config(text="RENOVAR", fg=AMBER)
        elif validity and validity not in ("-", "—"):
            label.config(text=validity, fg=GREEN)
        else:
            label.config(text="—", fg=RED)

    def _apply_lookup_results(self, update_identity: bool = True) -> None:
        if self.operation.get() == "MELI":
            return
        result_map = index_results(self.lookup_results)
        driver = self.parsed.drivers[0] if self.parsed.drivers else None
        if driver:
            result = result_map.get(("motorista", normalize_cpf(driver.cpf)), {})
            self._set_combo_from_result("BRK", result)
            label = self.validity_labels.get(("driver1", ""))
            if label:
                self._set_validity_label(label, result.get("validity"), result.get("status_brk"), result.get("status"))
        else:
            self.amazon_vars["BRK"].set(SELECT)
            self._set_label(("driver1", ""), None)
        if len(self.parsed.drivers) > 1:
            result = result_map.get(("motorista", normalize_cpf(self.parsed.drivers[1].cpf)), {})
            self.driver2_summary.set(f"Motorista 2 BRK: {result.get('status') or '—'}")
            label = self.validity_labels.get(("driver2", ""))
            if label:
                self._set_validity_label(label, result.get("validity"), result.get("status_brk"), result.get("status"))
        else:
            self.driver2_summary.set("Motorista 2 BRK: —")
        horse = next((v for v in self.parsed.vehicles if v.role == "Cavalo"), None)
        trailer = next((v for v in self.parsed.vehicles if v.role.startswith("Carreta")), None)
        self._apply_vehicle_result("Placa Cavalo BRK", horse, "horse")
        self._apply_vehicle_result("Placa Carreta BRK", trailer, "trailer")
        if update_identity and self.parsed.drivers:
            # The identity panel is rendered by identify_data; refresh its labels only when results change later.
            self._update_identity_validity()

    def _apply_vehicle_result(self, field: str, vehicle, key: str) -> None:
        if vehicle is None:
            self.amazon_vars[field].set(SELECT)
            self._set_label((key, ""), None)
            return
        result = self.result_map.get(("veiculo", normalize_plate(vehicle.plate)), {})
        self._set_combo_from_result(field, result)
        self._set_label((key, ""), result)

    def _set_combo_from_result(self, field: str, result: dict) -> None:
        value = result.get("status")
        if not value and str(result.get("error", "")).startswith("Nenhum registro elegível da AMAZON"):
            value = "Sem cadastro"
        if not value:
            self.amazon_vars[field].set(SELECT)
            return
        combo = self.amazon_combos[field]
        choices = list(combo.cget("values"))
        if value not in choices:
            combo.configure(values=tuple(choices) + (value,))
        self.amazon_vars[field].set(value)

    def _set_label(self, key: tuple[str, str], result: dict | None) -> None:
        label = self.validity_labels.get(key)
        if label:
            result = result or {}
            self._set_validity_label(label, result.get("validity"), result.get("status_brk"), result.get("status"))

    def _update_identity_validity(self) -> None:
        self._render_identity()

    def _operation_controls(self) -> dict:
        return {
            "amazon": {key: var.get() for key, var in self.amazon_vars.items()},
            "fleet": {"apta": self.fleet_apta.get(), "values": {key: var.get() for key, var in self.fleet_vars.items()}},
            "lweb": {"values": {key: var.get() for key, var in self.lweb_vars.items()}},
            "tractor_year": self.year_var.get(), "minimum_year": self.minimum_year.get(),
            "meli": {key: var.get() for key, var in self.meli_vars.items()}, "meli_use_vecfleet": self.meli_use_vecfleet.get(),
            "possui_carreta": self.possui_carreta.get(),
        }

    def generate(self) -> None:
        if not self.parsed.drivers and not self.parsed.vehicles:
            self.identify_data()
        try:
            text = (generate_amazon_validation(self.parsed, self.lookup_results, self._operation_controls())
                    if self.operation.get() == "AMAZON" else
                    generate_meli_validation(self.parsed, self._operation_controls()))
        except ValidationInputError as exc:
            messagebox.showerror("Validação incompleta", str(exc), parent=self.root)
            return
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)

    def copy_preview(self) -> None:
        text = self.preview.get("1.0", "end-1c")
        if not text.strip():
            messagebox.showinfo("Copiar validação", "Gere a validação antes de copiar.", parent=self.root)
            return
        copy_text_to_clipboard(self.root, text)
        self.identify_message.config(text="Validação copiada para a área de transferência.", fg=GREEN)

    def clear_validation(self) -> None:
        self.input_text.delete("1.0", "end")
        self.preview.delete("1.0", "end")
        self.parsed = ParsedInput()
        self.lookup_results.clear()
        self.result_map.clear()
        self.vehicle_role_vars.clear()
        self.validity_labels.pop(("driver2", ""), None)
        for child in self.identity_content.winfo_children():
            child.destroy()
        tk.Label(self.identity_content, text="A identificação preencherá aqui motorista(s) e placa(s).", bg=BG, fg="gray40", anchor="w").grid(row=0, column=0, sticky="w")
        for variables in (self.amazon_vars, self.fleet_vars, self.lweb_vars, self.meli_vars):
            for variable in variables.values():
                variable.set(SELECT)
        for combo in self.amazon_combos.values():
            combo.configure(values=STATUS_OPTIONS if combo == self.amazon_combos.get("BRK") else (CHECKLIST_OPTIONS if combo == self.amazon_combos.get("Checklist") else STANDARD_OPTIONS if combo in (self.amazon_combos.get("Onboarding"), self.amazon_combos.get("ET"), self.amazon_combos.get("TDD")) else STATUS_OPTIONS))
        for label in self.validity_labels.values():
            label.config(text="—", fg=RED)
        self.driver2_summary.set("Motorista 2 BRK: —")
        self.fleet_apta.set(False)
        self.possui_carreta.set(True)
        self._fleet_apta_changed()
        self.year_var.set("")
        self.minimum_year.set("2013")
        self.meli_use_vecfleet.set(True)
        self._refresh_meli_fields()
        self._refresh_vehicle_dependent_controls()
        self.identify_message.config(text="Validação limpa. Os relatórios carregados foram mantidos.", fg="gray35")

    def delete_loaded_data(self) -> None:
        if not any(self.store.is_loaded(kind) for kind in ("motorista", "veiculo")):
            messagebox.showinfo("Dados BRK", "Não há relatórios carregados para apagar.", parent=self.root)
            return
        if not messagebox.askyesno("Apagar dados carregados", "Apagar da memória os relatórios e a validação atual? Os arquivos originais não serão excluídos.", parent=self.root):
            return
        self.store.clear()
        for kind in self.paths:
            self.paths[kind].set("")
            self.status_widgets[kind].config(text="Não carregado", fg=RED)
        self.clear_validation()
        self.identify_message.config(text="Relatórios e validação apagados da memória.", fg="gray35")

    def _shortcut_f1(self, _event=None):
        if self.operation.get() == "MELI":
            self._set_meli_section("BRK", "OK")
            self._set_meli_section("CHECKS", "OK")
        else:
            trailer_selected = self.possui_carreta.get() and any(
                role_var.get().startswith("Carreta")
                for role_var in self.vehicle_role_vars.values()
            )
            for key in ("BRK", "Onboarding", "ET", "TDD", "Checklist", "Placa Cavalo BRK", "Placa Carreta BRK"):
                if key != "Placa Carreta BRK" or trailer_selected:
                    self.amazon_vars[key].set("OK")
        return "break"

    def _shortcut_f2(self, _event=None):
        if self.operation.get() == "MELI":
            if self.meli_use_vecfleet.get():
                self._set_meli_section("VEC FLEET", "OK")
        else:
            self.fleet_apta.set(True)
            self._fleet_apta_changed()
        return "break"

    def _shortcut_f3(self, _event=None):
        if self.operation.get() == "MELI":
            self._set_meli_section("LWEB", "OK")
        else:
            for var in self.lweb_vars.values():
                var.set("Cadastro")
        return "break"

    def _shortcut_f4(self, _event=None):
        if self.operation.get() == "MELI":
            if self.meli_use_vecfleet.get():
                self._set_meli_section("VEC FLEET", "Sem cadastro")
        else:
            for var in self.fleet_vars.values():
                var.set("Cadastro")
        return "break"

    def _set_meli_section(self, section: str, value: str) -> None:
        for (name, _key), variable in self.meli_vars.items():
            if name == section:
                variable.set(value)

    def close(self) -> None:
        self.store.clear()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    ReportImporterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
