from textual.widgets import OptionList
from textual.widgets.option_list import Option


class ArrowOptionList(OptionList):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._raw_labels: list[str] = []
        self._last_hl: int | None = None

    def set_items(self, items: list[tuple[str, str]], highlighted_idx: int = 0) -> None:
        self.clear_options()
        self._raw_labels = [label for _, label in items]
        for idx, (opt_id, label) in enumerate(items):
            prefix = "> " if idx == highlighted_idx else "  "
            self.add_option(Option(f"{prefix}{label}", id=opt_id))
        if items:
            self._last_hl = highlighted_idx
            self.highlighted = highlighted_idx

    def update_item_label(self, idx: int, new_label: str) -> None:
        if 0 <= idx < len(self._raw_labels):
            self._raw_labels[idx] = new_label
            prefix = "> " if self.highlighted == idx else "  "
            self.replace_option_prompt_at_index(idx, f"{prefix}{new_label}")

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        new_idx = event.option_index
        if (
            self._last_hl is not None
            and 0 <= self._last_hl < len(self._raw_labels)
            and self._last_hl != new_idx
        ):
            old_label = self._raw_labels[self._last_hl]
            self.replace_option_prompt_at_index(self._last_hl, f"  {old_label}")
        if 0 <= new_idx < len(self._raw_labels):
            self.replace_option_prompt_at_index(new_idx, f"> {self._raw_labels[new_idx]}")
            self._last_hl = new_idx