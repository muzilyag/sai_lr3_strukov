from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

from .fuzzy_math import AGGREGATORS, IMPLICATORS, Vector
from .fuzzy_system import (
    InferenceResult,
    KnowledgeBase,
    alg1_individual,
    alg2_aggregate,
    alg3_truth_levels,
)

matplotlib.use("Agg")


def plot_terms_and_inputs(
    kb: KnowledgeBase,
    inputs: dict[str, Vector],
    out_dir: Path,
    prefix: str,
) -> str:
    total_vars = len(kb.inputs) + 1
    fig, axes = plt.subplots(
        nrows=total_vars,
        ncols=1,
        figsize=(10, 3.2 * total_vars),
        layout="constrained",
    )
    if total_vars == 1:
        axes = [axes]

    for ax, (var_name, var) in zip(axes[:-1], kb.inputs.items()):
        for term_name, mu in var.terms.items():
            ax.plot(var.universe, mu, marker="o", label=term_name)
        if var_name in inputs:
            ax.plot(
                var.universe,
                inputs[var_name],
                color="black",
                linestyle="--",
                linewidth=2.5,
                marker="s",
                label="Входной факт A'",
            )
            ax.fill_between(var.universe, inputs[var_name], color="gray", alpha=0.15)
        ax.set_title(f"Входная переменная: '{var_name}'")
        ax.set_ylabel("μ(x)")
        ax.set_ylim(-0.05, 1.1)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0))

    out_ax = axes[-1]
    for term_name, mu in kb.output.terms.items():
        out_ax.plot(kb.output.universe, mu, marker="o", label=term_name)
    out_ax.set_title(f"Выходная переменная: '{kb.output_name}'")
    out_ax.set_ylabel("μ(y)")
    out_ax.set_ylim(-0.05, 1.1)
    out_ax.grid(True, alpha=0.3)
    out_ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0))

    file_path = out_dir / f"{prefix}_1_terms_and_inputs.png"
    fig.savefig(file_path, dpi=150)
    plt.close(fig)
    return str(file_path)


def plot_inference_results(
    kb: KnowledgeBase,
    imp_key: str,
    agg_key: str,
    inputs: dict[str, Vector],
    out_dir: Path,
    prefix: str,
) -> str:
    imp_name, imp_op = IMPLICATORS[imp_key]
    agg_name, agg_op = AGGREGATORS[agg_key]
    out_u = kb.output.universe

    runs: list[tuple[str, InferenceResult]] = []
    if len(kb.inputs) == 1:
        r1 = alg1_individual(kb, imp_op, agg_op, inputs)
        r2 = alg2_aggregate(kb, imp_op, agg_op, inputs)
        if r1:
            runs.append(("Алгоритм 1 (Индивидуальные выходы)", r1))
        if r2:
            runs.append(("Алгоритм 2 (Агрегация матриц R)", r2))
    r3 = alg3_truth_levels(kb, imp_op, agg_op, inputs)
    runs.append(("Алгоритм 3 (Уровни истинности alpha)", r3))

    fig, axes = plt.subplots(
        nrows=len(runs),
        ncols=1,
        figsize=(10, 3.6 * len(runs)),
        layout="constrained",
    )
    if len(runs) == 1:
        axes = [axes]

    for ax, (title, res) in zip(axes, runs):
        if res.b_primes:
            for i, b_i in enumerate(res.b_primes, start=1):
                lbl = f"R{i}" if res.alphas is None else f"R{i} (α={res.alphas[i-1]:.2f})"
                ax.plot(out_u, b_i, linestyle=":", marker=".", alpha=0.7, label=lbl)

        ax.plot(
            out_u,
            res.b_final,
            color="tab:blue",
            linewidth=2.5,
            marker="o",
            label="Итоговый выход B'",
        )
        ax.fill_between(out_u, res.b_final, color="tab:blue", alpha=0.2)
        ax.axvline(
            res.y_star,
            color="tab:red",
            linestyle="--",
            linewidth=2.0,
            label=f"Центр тяжести y* = {res.y_star:+.2f}",
        )
        ax.set_title(f"{title}\nИмпликация: {imp_name} | Агрегация: {agg_name}", fontsize=11)
        ax.set_ylabel("μ(y)")
        ax.set_ylim(-0.05, 1.1)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0))

    file_path = out_dir / f"{prefix}_2_inference_and_cog.png"
    fig.savefig(file_path, dpi=150)
    plt.close(fig)
    return str(file_path)


def plot_implications_comparison(
    kb: KnowledgeBase,
    agg_key: str,
    inputs: dict[str, Vector],
    out_dir: Path,
    prefix: str,
) -> str:
    agg_name, agg_op = AGGREGATORS[agg_key]
    alg_fn = alg1_individual if len(kb.inputs) == 1 else alg3_truth_levels
    out_u = kb.output.universe

    fig, ax = plt.subplots(figsize=(10, 4.5), layout="constrained")
    markers = ["o", "s", "^", "D", "v"]

    for (imp_name, imp_op), marker in zip(IMPLICATORS.values(), markers):
        res = alg_fn(kb, imp_op, agg_op, inputs)
        if res is not None:
            ax.plot(
                out_u,
                res.b_final,
                marker=marker,
                linewidth=2.0,
                label=f"{imp_name} [y* = {res.y_star:+.2f}]",
            )

    ax.set_title(f"Сравнение типов импликаций ({alg_fn.__name__})\nАгрегация: {agg_name}", fontsize=11)
    ax.set_xlabel(kb.output_name)
    ax.set_ylabel("μ_B'(y)")
    ax.set_ylim(-0.05, 1.1)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0))

    file_path = out_dir / f"{prefix}_3_implications_comparison.png"
    fig.savefig(file_path, dpi=150)
    plt.close(fig)
    return str(file_path)


def generate_all_plots(
    kb: KnowledgeBase,
    imp_key: str,
    agg_key: str,
    inputs: dict[str, Vector],
    out_dir_path: str = "./plots",
) -> list[str]:
    out_dir = Path(out_dir_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"kb_{len(kb.inputs)}var"

    return [
        plot_terms_and_inputs(kb, inputs, out_dir, prefix),
        plot_inference_results(kb, imp_key, agg_key, inputs, out_dir, prefix),
        plot_implications_comparison(kb, agg_key, inputs, out_dir, prefix),
    ]