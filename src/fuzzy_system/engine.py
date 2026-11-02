from collections.abc import Callable
from functools import wraps

from ..fuzzy_math import *
from .models import InferenceResult, KnowledgeBase


def single_input_only(func: Callable[..., InferenceResult | None]):
    @wraps(func)
    def wrapper(kb: KnowledgeBase, *args, **kwargs) -> InferenceResult | None:
        if len(kb.inputs) != 1:
            return None
        return func(kb, *args, **kwargs)
    return wrapper


def interpret_output(kb: KnowledgeBase, res: InferenceResult) -> tuple[str, str]:
    b_final = res.b_final
    y_star = res.y_star
    max_mu = max(b_final) if b_final else 0.0
    min_mu = min(b_final) if b_final else 0.0

    if max_mu == 0.0 or (max_mu - min_mu < 1e-6):
        return "неопределённо (равномерное плато)", f"Невозможно выбрать терм (y* = {y_star:g})"

    out_u = kb.output.universe
    candidates = (
        (
            abs(defuzzify_cog(out_u, term_mu) - y_star),
            -calc_compatibility_degree(b_final, term_mu),
            term_name,
        )
        for term_name, term_mu in kb.output.terms.items()
    )
    _, neg_compat, best_term = min(candidates)
    best_compat = -neg_compat

    action = f"'{kb.output_name}' -> {best_term} (y* = {y_star:+.2f})"
    return f"'{best_term}' (совм. {best_compat:.2f})", action


@single_input_only
def alg1_individual(
    kb: KnowledgeBase,
    imp: FuzzyOp,
    agg: FuzzyOp,
    inputs: dict[str, Vector] | None = None,
) -> InferenceResult:
    active_inputs = inputs or kb.default_inputs
    var_name = next(iter(kb.inputs))
    a_prime = active_inputs[var_name]
    in_terms = kb.inputs[var_name].terms
    out_terms = kb.output.terms

    b_primes: Matrix = [
        max_min_composition(
            a_prime,
            build_relation_matrix(in_terms[r.conditions[var_name]], out_terms[r.conclusion], imp),
        )
        for r in kb.rules
    ]
    b_final = aggregate_vectors(b_primes, agg)
    y_star = defuzzify_cog(kb.output.universe, b_final)
    return InferenceResult(b_final=b_final, y_star=y_star, b_primes=b_primes)


@single_input_only
def alg2_aggregate(
    kb: KnowledgeBase,
    imp: FuzzyOp,
    agg: FuzzyOp,
    inputs: dict[str, Vector] | None = None,
) -> InferenceResult:
    active_inputs = inputs or kb.default_inputs
    var_name = next(iter(kb.inputs))
    a_prime = active_inputs[var_name]
    in_terms = kb.inputs[var_name].terms
    out_terms = kb.output.terms

    r_matrices: list[Matrix] = [
        build_relation_matrix(in_terms[r.conditions[var_name]], out_terms[r.conclusion], imp)
        for r in kb.rules
    ]
    r_total = aggregate_matrices(r_matrices, agg)
    b_final = max_min_composition(a_prime, r_total)
    y_star = defuzzify_cog(kb.output.universe, b_final)
    return InferenceResult(b_final=b_final, y_star=y_star, r_total=r_total)


def alg3_truth_levels(
    kb: KnowledgeBase,
    imp: FuzzyOp,
    agg: FuzzyOp,
    inputs: dict[str, Vector] | None = None,
) -> InferenceResult:
    active_inputs = inputs or kb.default_inputs
    out_terms = kb.output.terms

    alphas: Vector = [
        min(
            calc_compatibility_degree(active_inputs[var], kb.inputs[var].terms[term])
            for var, term in r.conditions.items()
        )
        for r in kb.rules
    ]
    b_primes: Matrix = [
        apply_alpha_implication(alpha, out_terms[r.conclusion], imp)
        for alpha, r in zip(alphas, kb.rules)
    ]
    b_final = aggregate_vectors(b_primes, agg)
    y_star = defuzzify_cog(kb.output.universe, b_final)
    return InferenceResult(b_final=b_final, y_star=y_star, b_primes=b_primes, alphas=alphas)