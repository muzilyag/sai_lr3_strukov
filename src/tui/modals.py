from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, OptionList, Static

from ..fuzzy_math import Vector
from ..fuzzy_system import KnowledgeBase
from ..utils import fuzzify_crisp_value
from .widgets import ArrowOptionList


class OperatorSelectModal(ModalScreen[str | None]):
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "cancel", "Отмена", key_display="Esc"),
    ]

    def __init__(self, title: str, items: dict[str, tuple[str, object]], current_key: str) -> None:
        super().__init__()
        self.modal_title = title
        self.items = items
        self.current_key = current_key

    def compose(self) -> ComposeResult:
        with Vertical(id="op_modal_box"):
            yield Label(self.modal_title, id="op_modal_title")
            yield ArrowOptionList(id="op_list")

    def on_mount(self) -> None:
        op_list = self.query_one("#op_list", ArrowOptionList)
        keys = list(self.items.keys())
        cur_idx = keys.index(self.current_key) if self.current_key in keys else 0
        formatted = [
            (k, f"{idx}. {label} [текущий]" if k == self.current_key else f"{idx}. {label}")
            for idx, (k, (label, _)) in enumerate(self.items.items(), start=1)
        ]
        formatted.append(("__cancel__", "0. Назад (без изменений)"))
        op_list.set_items(formatted, highlighted_idx=cur_idx)
        op_list.focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    @on(OptionList.OptionSelected, "#op_list")
    def on_selected(self, event: OptionList.OptionSelected) -> None:
        opt_id = str(event.option_id)
        if opt_id == "__cancel__":
            self.dismiss(None)
        else:
            self.dismiss(opt_id)


class InputFactModal(ModalScreen[tuple[dict[str, Vector], str] | None]):
    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "back_or_cancel", "Назад / Отмена", key_display="Esc"),
    ]

    def __init__(self, kb: KnowledgeBase, current_inputs: dict[str, Vector]) -> None:
        super().__init__()
        self.kb = kb
        self.current_inputs = current_inputs
        self.var_names = list(kb.inputs.keys())
        self.current_step: str = "mode"
        self.term_var_idx: int = 0
        self.chosen_terms: dict[str, str] = {}

    def compose(self) -> ComposeResult:
        with Vertical(id="modal_box"):
            yield Label("ВЫБЕРИТЕ СПОСОБ ЗАДАНИЯ ВХОДА A'", id="modal_title")

            with Vertical(id="step_mode", classes="step_box"):
                yield ArrowOptionList(id="mode_list")

            with Vertical(id="step_term", classes="step_box"):
                yield Label("", id="term_step_label", classes="field_label")
                yield ArrowOptionList(id="term_step_list")

            with Vertical(id="step_crisp", classes="step_box"):
                for idx, var_name in enumerate(self.var_names):
                    u = self.kb.inputs[var_name].universe
                    u_min, u_max = min(u), max(u)
                    yield Label(
                        f"Переменная '{var_name}' (диапазон [{u_min:g} .. {u_max:g}]):",
                        classes="field_label",
                    )
                    yield Input(placeholder=f"Число от {u_min:g} до {u_max:g}", id=f"crisp_{idx}")
                yield Label("Действие (Tab для перехода к списку):", classes="field_label")
                yield ArrowOptionList(id="crisp_actions", classes="action_list")

            with Vertical(id="step_custom", classes="step_box"):
                for idx, var_name in enumerate(self.var_names):
                    u = self.kb.inputs[var_name].universe
                    u_str = ", ".join(f"{x:g}" for x in u)
                    curr_str = " ".join(f"{v:.2f}" for v in self.current_inputs[var_name])
                    yield Label(
                        f"'{var_name}' (U = [{u_str}], нужно {len(u)} чисел):",
                        classes="field_label",
                    )
                    yield Input(value=curr_str, id=f"custom_{idx}")
                yield Label("Действие (Tab для перехода к списку):", classes="field_label")
                yield ArrowOptionList(id="custom_actions", classes="action_list")

            yield Static("", id="modal_error", markup=False)

    def on_mount(self) -> None:
        mode_list = self.query_one("#mode_list", ArrowOptionList)
        mode_list.set_items(
            [
                ("crisp", "1. Ввести точное число (авто-фазификация)"),
                ("term", "2. Выбрать словесный терм из базы"),
                ("custom", "3. Задать вектор вручную"),
                ("default", "4. Сбросить к значениям по умолчанию"),
                ("__cancel__", "0. Отмена (закрыть окно)"),
            ],
            highlighted_idx=0,
        )
        action_items = [
            ("apply", "1. Применить введённые значения"),
            ("back", "0. Назад (без сохранения)"),
        ]
        self.query_one("#crisp_actions", ArrowOptionList).set_items(action_items, highlighted_idx=0)
        self.query_one("#custom_actions", ArrowOptionList).set_items(action_items, highlighted_idx=0)
        self._show_step("mode")

    def _show_step(self, step: str) -> None:
        self.current_step = step
        self.query_one("#modal_error", Static).update("")
        self.query_one("#step_mode", Vertical).display = step == "mode"
        self.query_one("#step_term", Vertical).display = step == "term"
        self.query_one("#step_crisp", Vertical).display = step == "crisp"
        self.query_one("#step_custom", Vertical).display = step == "custom"

        title = self.query_one("#modal_title", Label)
        if step == "mode":
            title.update("ВЫБЕРИТЕ СПОСОБ ЗАДАНИЯ ВХОДА A'")
            self.query_one("#mode_list", ArrowOptionList).focus()
        elif step == "term":
            title.update("ВЫБОР СЛОВЕСНОГО ТЕРМА")
            self.term_var_idx = 0
            self.chosen_terms.clear()
            self._load_term_step()
        elif step == "crisp":
            title.update("ВВОД ТОЧНЫХ ЧИСЛОВЫХ ЗНАЧЕНИЙ")
            self.query_one("#crisp_0", Input).focus()
        elif step == "custom":
            title.update("РУЧНОЙ ВВОД ВЕКТОРА СТЕПЕНЕЙ ПРИНАДЛЕЖНОСТИ")
            self.query_one("#custom_0", Input).focus()

    def _load_term_step(self) -> None:
        var_name = self.var_names[self.term_var_idx]
        total = len(self.var_names)
        lbl = self.query_one("#term_step_label", Label)
        lbl.update(f"Шаг {self.term_var_idx + 1} из {total}. Переменная '{var_name}':")

        t_list = self.query_one("#term_step_list", ArrowOptionList)
        terms = list(self.kb.inputs[var_name].terms.keys())
        items = [(t, f"{i}. {t}") for i, t in enumerate(terms, start=1)]
        items.append(("__back__", "0. Назад"))
        t_list.set_items(items, highlighted_idx=0)
        t_list.focus()

    def action_back_or_cancel(self) -> None:
        if self.current_step == "term" and self.term_var_idx > 0:
            self.term_var_idx -= 1
            self._load_term_step()
        elif self.current_step != "mode":
            self._show_step("mode")
        else:
            self.dismiss(None)

    @on(OptionList.OptionSelected, "#mode_list")
    def on_mode_selected(self, event: OptionList.OptionSelected) -> None:
        mode_id = str(event.option_id)
        if mode_id == "__cancel__":
            self.dismiss(None)
        elif mode_id == "default":
            self.dismiss((dict(self.kb.default_inputs), "По умолчанию (из базы)"))
        else:
            self._show_step(mode_id)

    @on(OptionList.OptionSelected, "#term_step_list")
    def on_term_step_selected(self, event: OptionList.OptionSelected) -> None:
        opt_id = str(event.option_id)
        if opt_id == "__back__":
            if self.term_var_idx > 0:
                self.term_var_idx -= 1
                self._load_term_step()
            else:
                self._show_step("mode")
            return

        var_name = self.var_names[self.term_var_idx]
        self.chosen_terms[var_name] = opt_id
        if self.term_var_idx + 1 < len(self.var_names):
            self.term_var_idx += 1
            self._load_term_step()
        else:
            new_inputs = {
                v: list(self.kb.inputs[v].terms[t])
                for v, t in self.chosen_terms.items()
            }
            chosen_str = ", ".join(f"{v}='{t}'" for v, t in self.chosen_terms.items())
            self.dismiss((new_inputs, f"Терм ({chosen_str})"))

    def _validate_single_crisp(self, idx: int) -> float | None:
        err_box = self.query_one("#modal_error", Static)
        var_name = self.var_names[idx]
        u = self.kb.inputs[var_name].universe
        u_min, u_max = min(u), max(u)
        raw = self.query_one(f"#crisp_{idx}", Input).value.strip().replace(",", ".")
        try:
            val = float(raw)
        except ValueError:
            err_box.update(f"Ошибка: введите корректное число для '{var_name}'.")
            return None
        if not (u_min <= val <= u_max):
            err_box.update(f"Ошибка: '{var_name}' вне диапазона [{u_min:g} .. {u_max:g}].")
            return None
        err_box.update("")
        return val

    def _validate_single_custom(self, idx: int) -> Vector | None:
        err_box = self.query_one("#modal_error", Static)
        var_name = self.var_names[idx]
        u = self.kb.inputs[var_name].universe
        raw = self.query_one(f"#custom_{idx}", Input).value.strip().replace(",", ".")
        try:
            vals = [float(x) for x in raw.split()]
        except ValueError:
            err_box.update(f"Ошибка: в векторе '{var_name}' должны быть только числа.")
            return None
        if len(vals) != len(u) or any(not (0.0 <= v <= 1.0) for v in vals):
            err_box.update(f"Ошибка: для '{var_name}' нужно ровно {len(u)} чисел от 0 до 1.")
            return None
        err_box.update("")
        return vals

    def _submit_all_crisp(self) -> None:
        new_inputs: dict[str, Vector] = {}
        labels: list[str] = []
        for i, var_name in enumerate(self.var_names):
            val = self._validate_single_crisp(i)
            if val is None:
                self.query_one(f"#crisp_{i}", Input).focus()
                return
            new_inputs[var_name] = fuzzify_crisp_value(self.kb.inputs[var_name].universe, val)
            labels.append(f"{var_name}={val:g}")
        self.dismiss((new_inputs, f"Чёткие числа ({', '.join(labels)})"))

    def _submit_all_custom(self) -> None:
        new_inputs: dict[str, Vector] = {}
        for i, var_name in enumerate(self.var_names):
            vals = self._validate_single_custom(i)
            if vals is None:
                self.query_one(f"#custom_{i}", Input).focus()
                return
            new_inputs[var_name] = vals
        self.dismiss((new_inputs, "Задано вручную (вектор)"))

    @on(OptionList.OptionSelected, "#crisp_actions")
    def on_crisp_action(self, event: OptionList.OptionSelected) -> None:
        if str(event.option_id) == "back":
            self._show_step("mode")
        else:
            self._submit_all_crisp()

    @on(OptionList.OptionSelected, "#custom_actions")
    def on_custom_action(self, event: OptionList.OptionSelected) -> None:
        if str(event.option_id) == "back":
            self._show_step("mode")
        else:
            self._submit_all_custom()

    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted) -> None:
        inp_id = event.input.id or ""
        if inp_id.startswith("crisp_"):
            idx = int(inp_id.split("_")[1])
            if self._validate_single_crisp(idx) is None:
                return
            if idx + 1 < len(self.var_names):
                self.query_one(f"#crisp_{idx + 1}", Input).focus()
            else:
                self._submit_all_crisp()

        elif inp_id.startswith("custom_"):
            idx = int(inp_id.split("_")[1])
            if self._validate_single_custom(idx) is None:
                return
            if idx + 1 < len(self.var_names):
                self.query_one(f"#custom_{idx + 1}", Input).focus()
            else:
                self._submit_all_custom()