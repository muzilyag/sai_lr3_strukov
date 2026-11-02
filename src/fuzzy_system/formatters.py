from collections.abc import Callable

from prettytable import PrettyTable

from ..fuzzy_math import AGGREGATORS, IMPLICATORS, FuzzyOp, Vector
from ..utils import format_fuzzy_set, format_matrix_table
from .engine import alg1_individual, alg2_aggregate, alg3_truth_levels, interpret_output
from .models import InferenceResult, KnowledgeBase


def format_status_table(
    kb_path: str,
    kb: KnowledgeBase,
    imp_name: str,
    agg_name: str,
    current_inputs: dict[str, Vector],
    input_mode_label: str,
) -> str:
    table = PrettyTable()
    table.field_names = ["Параметр системы", "Текущее значение"]
    table.align["Параметр системы"] = "l"
    table.align["Текущее значение"] = "l"

    table.add_row(["База знаний", f"{kb_path} (входов: {len(kb.inputs)}, правил: {len(kb.rules)})"])
    table.add_row(["Импликатор", imp_name])
    table.add_row(["Оператор агрегации", agg_name])
    table.add_row(["Режим входного факта A'", input_mode_label])

    for var_name, mu in current_inputs.items():
        u = kb.inputs[var_name].universe
        table.add_row([f"Вход '{var_name}'", format_fuzzy_set(u, mu)])

    return str(table)


def print_status_table(
    kb_path: str,
    kb: KnowledgeBase,
    imp_name: str,
    agg_name: str,
    current_inputs: dict[str, Vector],
    input_mode_label: str,
) -> None:
    print(f"\n{format_status_table(kb_path, kb, imp_name, agg_name, current_inputs, input_mode_label)}")


def format_kb_report(kb: KnowledgeBase) -> str:
    blocks: list[str] = [f"БАЗА ЗНАНИЙ: {kb.description}"]

    for var_name, var in kb.inputs.items():
        t_table = PrettyTable()
        t_table.field_names = ["Терм \\ Шкала U", *[f"{u:g}" for u in var.universe]]
        t_table.align["Терм \\ Шкала U"] = "l"
        for term_name, mu in var.terms.items():
            t_table.add_row([term_name, *[f"{val:.2f}" for val in mu]])
        blocks.append(f"\nВходная переменная '{var_name}':\n{t_table}")

    out_table = PrettyTable()
    out_table.field_names = ["Терм \\ Шкала U", *[f"{u:g}" for u in kb.output.universe]]
    out_table.align["Терм \\ Шкала U"] = "l"
    for term_name, mu in kb.output.terms.items():
        out_table.add_row([term_name, *[f"{val:.2f}" for val in mu]])
    blocks.append(f"\nВыходная переменная '{kb.output_name}':\n{out_table}")

    r_table = PrettyTable()
    r_table.field_names = ["№", "Условие (ЕСЛИ)", f"Заключение (ТО '{kb.output_name}')"]
    r_table.align["Условие (ЕСЛИ)"] = "l"
    r_table.align[f"Заключение (ТО '{kb.output_name}')"] = "l"
    for i, rule in enumerate(kb.rules, start=1):
        conds = " И ".join(f"'{k}' = {v}" for k, v in rule.conditions.items())
        r_table.add_row([f"R{i}", conds, rule.conclusion])
    blocks.append(f"\nБаза лингвистических правил:\n{r_table}")

    return "\n".join(blocks)


def show_kb(kb: KnowledgeBase) -> None:
    print(f"\n{format_kb_report(kb)}")


def format_single_result(title: str, kb: KnowledgeBase, res: InferenceResult, include_summary: bool = True) -> str:
    out_u = kb.output.universe
    blocks: list[str] = [title]

    if res.b_primes and res.alphas is None:
        table = PrettyTable()
        table.field_names = ["Правило", *[f"{u:g}" for u in out_u]]
        for i, b_i in enumerate(res.b_primes, start=1):
            table.add_row([f"B'_{i} (R{i})", *[f"{val:.2f}" for val in b_i]])
        blocks.append(str(table))

    if res.r_total:
        in_var = next(iter(kb.inputs.values()))
        blocks.append(
            format_matrix_table(
                res.r_total,
                row_labels=in_var.universe,
                col_labels=out_u,
                title="Агрегированная матрица правил R:",
            )
        )

    if res.alphas and res.b_primes:
        table = PrettyTable()
        table.field_names = ["Правило", "alpha", *[f"{u:g}" for u in out_u]]
        for i, (alpha, b_i) in enumerate(zip(res.alphas, res.b_primes), start=1):
            table.add_row([f"R{i}", f"{alpha:.2f}", *[f"{val:.2f}" for val in b_i]])
        table.add_row(["Итог B'", "-", *[f"{val:.2f}" for val in res.b_final]])
        blocks.append(str(table))

    if include_summary:
        term_verdict, action_verdict = interpret_output(kb, res)
        summary = PrettyTable()
        summary.field_names = ["Показатель вывода", "Значение"]
        summary.align["Показатель вывода"] = "l"
        summary.align["Значение"] = "l"
        summary.add_row(["Центр тяжести (y*)", f"{res.y_star:+.2f}"])
        summary.add_row(["Ближайший терм", term_verdict])
        summary.add_row(["Итоговое заключение", action_verdict])
        blocks.append(str(summary))

    return "\n".join(blocks)


def print_result(title: str, kb: KnowledgeBase, res: InferenceResult | None) -> None:
    if res is None:
        return
    print(f"\n{format_single_result(title, kb, res, include_summary=True)}")


def format_full_inference_report(
    kb: KnowledgeBase,
    imp_op: FuzzyOp,
    agg_op: FuzzyOp,
    inputs: dict[str, Vector],
) -> str:
    out_u = kb.output.universe
    blocks: list[str] = []

    if len(kb.inputs) == 1:
        r1 = alg1_individual(kb, imp_op, agg_op, inputs)
        r2 = alg2_aggregate(kb, imp_op, agg_op, inputs)
        r3 = alg3_truth_levels(kb, imp_op, agg_op, inputs)

        b_table = PrettyTable()
        b_table.field_names = ["Механизм", *[f"{u:g}" for u in out_u], "y*"]
        b_table.align["Механизм"] = "l"
        b_table.align["y*"] = "r"

        for name, res in [
            ("Алг. 1 (Индив.)", r1),
            ("Алг. 2 (Матрица R)", r2),
            ("Алг. 3 (Уровни alpha)", r3),
        ]:
            if res is not None:
                b_table.add_row([name, *[f"{val:.2f}" for val in res.b_final], f"{res.y_star:+.2f}"])

        term_verdict, final_action = interpret_output(kb, r3)
        verdict_table = PrettyTable()
        verdict_table.field_names = ["Показатель вывода", "Значение"]
        verdict_table.align["Показатель вывода"] = "l"
        verdict_table.align["Значение"] = "l"
        verdict_table.add_row(["Центр тяжести (y*)", f"{r3.y_star:+.2f}"])
        verdict_table.add_row(["Ближайший терм", term_verdict])
        verdict_table.add_row(["Итоговое заключение", final_action])

        blocks.append(f"СВОДНЫЙ РЕЗУЛЬТАТ ВЫВОДА (B' И ЦЕНТР ТЯЖЕСТИ)\n{b_table}\n{verdict_table}")

        if r1:
            blocks.append(format_single_result("АЛГОРИТМ 1 (Индивидуальные выходы правил)", kb, r1, include_summary=False))
        if r2:
            blocks.append(format_single_result("АЛГОРИТМ 2 (Первоначальная агрегация правил)", kb, r2, include_summary=False))
        blocks.append(format_single_result("АЛГОРИТМ 3 (Уровни истинности предпосылок)", kb, r3, include_summary=False))
    else:
        r3 = alg3_truth_levels(kb, imp_op, agg_op, inputs)
        blocks.append(format_single_result("АЛГОРИТМ 3 (Уровни истинности предпосылок)", kb, r3, include_summary=True))

    return "\n\n".join(blocks)


def format_implications_comparison(
    kb: KnowledgeBase,
    alg_func: Callable[..., InferenceResult | None],
    agg_key: str = "max",
    inputs: dict[str, Vector] | None = None,
) -> str:
    agg_name, agg_op = AGGREGATORS[agg_key]
    out_u = kb.output.universe

    table = PrettyTable()
    table.field_names = ["Импликатор", *[f"{u:g}" for u in out_u], "y*"]
    table.align["Импликатор"] = "l"
    table.align["y*"] = "r"

    for imp_name, imp_op in IMPLICATORS.values():
        res = alg_func(kb, imp_op, agg_op, inputs)
        if res is not None:
            short_name = imp_name.split(" (")[0]
            table.add_row([short_name, *[f"{val:.2f}" for val in res.b_final], f"{res.y_star:+.2f}"])

    return f"СРАВНЕНИЕ ИМПЛИКАЦИЙ ({alg_func.__name__} | Агрегация: {agg_name})\n{table}"


def compare_implications(
    kb: KnowledgeBase,
    alg_func: Callable[..., InferenceResult | None],
    agg_key: str = "max",
    inputs: dict[str, Vector] | None = None,
) -> None:
    print(f"\n{format_implications_comparison(kb, alg_func, agg_key, inputs)}")