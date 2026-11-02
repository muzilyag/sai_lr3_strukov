from typing import ClassVar

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Label, OptionList, Static, TabbedContent, TabPane

from ..fuzzy_math import AGGREGATORS, IMPLICATORS, Vector
from ..fuzzy_system import (
    KnowledgeBase,
    format_full_inference_report,
    format_kb_report,
    format_status_table,
    load_kb,
)
from ..plots import generate_all_plots
from .modals import InputFactModal, OperatorSelectModal
from .widgets import ArrowOptionList

KB_1VAR = "./kb/kb_1var.json"
KB_3VARS = "./kb/kb_3vars.json"


class FuzzyLogicApp(App):
    CSS_PATH = "styles.tcss"
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("left", "switch_tab('tab_inference')", "Вывод", key_display="Left"),
        Binding("right", "switch_tab('tab_kb')", "База знаний", key_display="Right"),
        Binding("shift+up", "scroll_report(-1)", "Скролл вверх", key_display="Shift+Up", priority=True),
        Binding("shift+down", "scroll_report(1)", "Скролл вниз", key_display="Shift+Down", priority=True),
        Binding("b", "switch_kb", "Сменить базу", key_display="B"),
        Binding("i", "edit_inputs", "Вход A'", key_display="I"),
        Binding("r", "run_inference", "Расчёт", key_display="R"),
        Binding("p", "save_plots", "Графики", key_display="P"),
        Binding("q", "quit", "Выход", key_display="Q"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.kb_path: str = KB_1VAR
        self.kb: KnowledgeBase = load_kb(self.kb_path)
        self.current_inputs: dict[str, Vector] = dict(self.kb.default_inputs)
        self.input_mode_label: str = "По умолчанию (из базы)"
        self.imp_key: str = "mamdani"
        self.agg_key: str = "max"
        self.live_mode: bool = True

    def compose(self) -> ComposeResult:
        with Horizontal(id="main_body"):
            with Vertical(id="sidebar"):
                yield Label("МЕНЮ УПРАВЛЕНИЯ", id="sidebar_title")
                yield ArrowOptionList(id="menu_list")
            with Vertical(id="content_area"), TabbedContent(id="tabs"):
                with TabPane("1. Логический вывод", id="tab_inference"), VerticalScroll(
                    id="scroll_inference", classes="report_scroll"
                ):
                    yield Static("", id="view_inference", markup=False)
                with TabPane("2. База знаний", id="tab_kb"), VerticalScroll(
                    id="scroll_kb", classes="report_scroll"
                ):
                    yield Static("", id="view_kb", markup=False)
        yield Static("", id="status_panel", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        menu = self.query_one("#menu_list", ArrowOptionList)
        menu.set_items(self._get_menu_items(), highlighted_idx=0)
        self._refresh_status_and_kb()
        self._refresh_calculations()
        menu.focus()

    def _get_menu_items(self) -> list[tuple[str, str]]:
        next_kb = "3 входа" if self.kb_path == KB_1VAR else "1 вход"
        live_str = "ВКЛ" if self.live_mode else "ВЫКЛ"
        return [
            ("switch_kb", f"1. Сменить базу (на {next_kb})"),
            ("select_imp", "2. Выбрать импликатор"),
            ("select_agg", "3. Выбрать агрегатор"),
            ("edit_inputs", "4. Задать входной факт A'"),
            ("toggle_live", f"5. Авто-пересчёт: {live_str}"),
            ("run_calc", "6. Запустить логический вывод"),
            ("save_plots", "7. Сохранить графики"),
            ("exit_app", "0. Выход"),
        ]

    def action_switch_tab(self, tab_id: str) -> None:
        if len(self.screen_stack) > 1:
            return
        self.query_one("#tabs", TabbedContent).active = tab_id
        self.query_one("#menu_list", ArrowOptionList).focus()

    def action_scroll_report(self, direction: int) -> None:
        if len(self.screen_stack) > 1:
            return
        active_tab = self.query_one("#tabs", TabbedContent).active
        scroll_id = "#scroll_inference" if active_tab == "tab_inference" else "#scroll_kb"
        scroller = self.query_one(scroll_id, VerticalScroll)
        scroller.scroll_relative(y=direction * 5, animate=False)

    @on(OptionList.OptionSelected, "#menu_list")
    def on_menu_selected(self, event: OptionList.OptionSelected) -> None:
        opt_id = str(event.option_id)
        match opt_id:
            case "switch_kb":
                self.action_switch_kb()
            case "select_imp":
                self.action_select_imp()
            case "select_agg":
                self.action_select_agg()
            case "edit_inputs":
                self.action_edit_inputs()
            case "toggle_live":
                self.live_mode = not self.live_mode
                live_str = "ВКЛ" if self.live_mode else "ВЫКЛ"
                menu = self.query_one("#menu_list", ArrowOptionList)
                menu.update_item_label(4, f"5. Авто-пересчёт: {live_str}")
                if self.live_mode:
                    self._refresh_calculations()
            case "run_calc":
                self.action_run_inference()
            case "save_plots":
                self.action_save_plots()
            case "exit_app":
                self.exit()

    def _refresh_status_and_kb(self) -> None:
        imp_name = IMPLICATORS[self.imp_key][0]
        agg_name = AGGREGATORS[self.agg_key][0]
        status_str = format_status_table(
            self.kb_path,
            self.kb,
            imp_name,
            agg_name,
            self.current_inputs,
            self.input_mode_label,
        )
        self.query_one("#status_panel", Static).update(status_str)
        self.query_one("#view_kb", Static).update(format_kb_report(self.kb))

    def _refresh_calculations(self) -> None:
        imp_op = IMPLICATORS[self.imp_key][1]
        agg_op = AGGREGATORS[self.agg_key][1]
        inf_report = format_full_inference_report(self.kb, imp_op, agg_op, self.current_inputs)
        self.query_one("#view_inference", Static).update(inf_report)

    def action_switch_kb(self) -> None:
        self.kb_path = KB_3VARS if self.kb_path == KB_1VAR else KB_1VAR
        self.kb = load_kb(self.kb_path)
        self.current_inputs = dict(self.kb.default_inputs)
        self.input_mode_label = "По умолчанию (из базы)"
        next_kb = "3 входа" if self.kb_path == KB_1VAR else "1 вход"
        menu = self.query_one("#menu_list", ArrowOptionList)
        menu.update_item_label(0, f"1. Сменить базу (на {next_kb})")
        self._refresh_status_and_kb()
        if self.live_mode:
            self._refresh_calculations()

    def action_select_imp(self) -> None:
        def _on_chosen(new_key: str | None) -> None:
            if new_key:
                self.imp_key = new_key
                self._refresh_status_and_kb()
                if self.live_mode:
                    self._refresh_calculations()

        self.push_screen(
            OperatorSelectModal("ВЫБЕРИТЕ ИМПЛИКАТОР", IMPLICATORS, self.imp_key),
            _on_chosen,
        )

    def action_select_agg(self) -> None:
        def _on_chosen(new_key: str | None) -> None:
            if new_key:
                self.agg_key = new_key
                self._refresh_status_and_kb()
                if self.live_mode:
                    self._refresh_calculations()

        self.push_screen(
            OperatorSelectModal("ВЫБЕРИТЕ ОПЕРАТОР АГРЕГАЦИИ", AGGREGATORS, self.agg_key),
            _on_chosen,
        )

    def action_edit_inputs(self) -> None:
        def _on_modal_close(result: tuple[dict[str, Vector], str] | None) -> None:
            if result is not None:
                self.current_inputs, self.input_mode_label = result
                self._refresh_status_and_kb()
                if self.live_mode:
                    self._refresh_calculations()

        self.push_screen(InputFactModal(self.kb, self.current_inputs), _on_modal_close)

    def action_run_inference(self) -> None:
        self._refresh_calculations()
        self.notify("Логический вывод обновлён", timeout=2)

    def action_save_plots(self) -> None:
        saved = generate_all_plots(self.kb, self.imp_key, self.agg_key, self.current_inputs)
        self.notify(f"Графики сохранены ({len(saved)} шт.)", timeout=3)