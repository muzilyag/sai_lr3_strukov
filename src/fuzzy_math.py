from collections.abc import Callable
from functools import reduce, wraps

type FuzzyOp = Callable[[float, float], float]
type Vector = list[float]
type Matrix = list[list[float]]


def rounded(ndigits: int):
    def decorator(func: Callable[..., float]) -> Callable[..., float]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> float:
            return round(func(*args, **kwargs), ndigits)
        return wrapper
    return decorator


def imp_mamdani(x: float, y: float) -> float:
    return min(x, y)


@rounded(6)
def imp_larsen(x: float, y: float) -> float:
    return x * y


@rounded(6)
def imp_lukasiewicz(x: float, y: float) -> float:
    return min(1.0, 1.0 - x + y)


def imp_godel(x: float, y: float) -> float:
    return 1.0 if x <= y else y


@rounded(6)
def imp_kleene_dienes(x: float, y: float) -> float:
    return max(1.0 - x, y)


IMPLICATORS: dict[str, tuple[str, FuzzyOp]] = {
    "mamdani": ("Мамдани (min{x, y})", imp_mamdani),
    "larsen": ("Ларсена (x * y)", imp_larsen),
    "lukasiewicz": ("Лукасевича (min{1, 1 - x + y})", imp_lukasiewicz),
    "godel": ("Гёделя (1 если x <= y иначе y)", imp_godel),
    "kleene_dienes": ("Клина-Дайнеса (max{1 - x, y})", imp_kleene_dienes),
}


def agg_max(x: float, y: float) -> float:
    return max(x, y)


@rounded(6)
def agg_probabilistic(x: float, y: float) -> float:
    return x + y - x * y


@rounded(6)
def agg_lukasiewicz(x: float, y: float) -> float:
    return min(x + y, 1.0)


AGGREGATORS: dict[str, tuple[str, FuzzyOp]] = {
    "max": ("Максимум (max{x, y})", agg_max),
    "probabilistic": ("Вероятностная (x + y - x*y)", agg_probabilistic),
    "lukasiewicz": ("Лукасевича (min{x + y, 1})", agg_lukasiewicz),
}


def build_relation_matrix(a: Vector, b: Vector, implicator: FuzzyOp) -> Matrix:
    return [[implicator(val_a, val_b) for val_b in b] for val_a in a]


def max_min_composition(a_prime: Vector, r_matrix: Matrix) -> Vector:
    return [
        max(min(a, r) for a, r in zip(a_prime, col))
        for col in zip(*r_matrix)
    ]


def aggregate_vectors(vectors: Matrix, aggregator: FuzzyOp) -> Vector:
    if not vectors:
        return []
    return reduce(
        lambda v1, v2: [aggregator(x, y) for x, y in zip(v1, v2)],
        vectors,
    )


def aggregate_matrices(matrices: list[Matrix], aggregator: FuzzyOp) -> Matrix:
    if not matrices:
        return []
    return reduce(
        lambda m1, m2: [
            [aggregator(x, y) for x, y in zip(row1, row2)]
            for row1, row2 in zip(m1, m2)
        ],
        matrices,
    )


def calc_compatibility_degree(a_prime: Vector, a_rule: Vector) -> float:
    return max(min(val_p, val_r) for val_p, val_r in zip(a_prime, a_rule))


def apply_alpha_implication(alpha: float, b_rule: Vector, implicator: FuzzyOp) -> Vector:
    return [implicator(alpha, val_b) for val_b in b_rule]


@rounded(2)
def defuzzify_cog(y_universe: Vector, b_prime: Vector) -> float:
    denominator: float = sum(b_prime)
    if denominator == 0:
        return 0.0
    numerator: float = sum(y * mu for y, mu in zip(y_universe, b_prime))
    return numerator / denominator