import questionary
from prettytable import PrettyTable

from .fuzzy_math import Matrix, Vector, rounded


def format_fuzzy_set(universe: Vector, mu_list: Vector) -> str:
    parts: list[str] = [f"{u:g}/{mu:.2f}" for u, mu in zip(universe, mu_list)]
    return " + ".join(parts)


def format_matrix_table(
    matrix: Matrix,
    row_labels: Vector | None = None,
    col_labels: Vector | None = None,
    title: str = "",
) -> str:
    table = PrettyTable()
    if col_labels:
        table.field_names = ["X \\ Y", *[f"{y:g}" for y in col_labels]]
    else:
        table.field_names = [f"Y{j+1}" for j in range(len(matrix[0]))]

    for i, row in enumerate(matrix):
        r_label = f"{row_labels[i]:g}" if row_labels else f"X{i+1}"
        table.add_row([r_label, *[f"{val:.2f}" for val in row]])

    return f"{title}\n{table}" if title else str(table)


def print_matrix(
    matrix: Matrix,
    row_labels: Vector | None = None,
    col_labels: Vector | None = None,
    title: str = "",
) -> None:
    print(f"\n{format_matrix_table(matrix, row_labels, col_labels, title)}")


@rounded(2)
def _calc_bell_mu(x: float, target: float, span: float) -> float:
    return max(0.0, 1.0 - abs(x - target) / span)


def fuzzify_crisp_value(universe: Vector, val: float) -> Vector:
    u_min, u_max = min(universe), max(universe)
    avg_step = (u_max - u_min) / max(1, len(universe) - 1)
    span = avg_step * 1.5 if avg_step > 0 else 1.0
    return [_calc_bell_mu(x, val, span) for x in universe]


def fuzzify_crisp_inputs(universes: dict[str, Vector]) -> dict[str, Vector] | None:
    result: dict[str, Vector] = {}
    for var_name, u in universes.items():
        u_min, u_max = min(u), max(u)
        while True:
            ans: str | None = questionary.text(
                f"Введите чёткое число для '{var_name}' (диапазон [{u_min:g} .. {u_max:g}]):"
            ).ask()
            if not ans:
                return None
            try:
                val = float(ans.replace(",", "."))
            except ValueError:
                print("Ошибка: нужно ввести одно число.")
                continue
            if not (u_min <= val <= u_max):
                print(f"Ошибка: число должно быть в пределах от {u_min:g} до {u_max:g}.")
                continue
            result[var_name] = fuzzify_crisp_value(u, val)
            break
    return result


def input_custom_facts(universes: dict[str, Vector]) -> dict[str, Vector] | None:
    custom_inputs: dict[str, Vector] = {}
    for var_name, u in universes.items():
        u_str = "  ".join(f"[{x:g}]" for x in u)
        print(f"\nОпорные точки для '{var_name}': {u_str}")
        ans: str | None = questionary.text(
            f"Введите {len(u)} степеней принадлежности от 0 до 1 (через пробел):"
        ).ask()
        if not ans:
            return None
        try:
            vals = [float(x) for x in ans.replace(",", ".").split()]
        except ValueError:
            print("Ошибка: ожидались вещественные числа.")
            return None
        if len(vals) != len(u) or any(not (0.0 <= v <= 1.0) for v in vals):
            print(f"Ошибка: нужно ровно {len(u)} чисел в диапазоне [0; 1].")
            return None
        custom_inputs[var_name] = vals
    return custom_inputs