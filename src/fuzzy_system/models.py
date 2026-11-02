import json
from dataclasses import dataclass

from ..fuzzy_math import Matrix, Vector


@dataclass(frozen=True)
class Variable:
    universe: Vector
    terms: dict[str, Vector]


@dataclass(frozen=True)
class Rule:
    conditions: dict[str, str]
    conclusion: str


@dataclass(frozen=True)
class KnowledgeBase:
    description: str
    inputs: dict[str, Variable]
    output_name: str
    output: Variable
    rules: list[Rule]
    default_inputs: dict[str, Vector]


@dataclass(frozen=True)
class InferenceResult:
    b_final: Vector
    y_star: float
    b_primes: Matrix | None = None
    r_total: Matrix | None = None
    alphas: Vector | None = None


def load_kb(kb_path: str) -> KnowledgeBase:
    with open(kb_path, "r", encoding="utf-8") as f:
        data: dict = json.load(f)

    inputs = {
        name: Variable(info["universe"], info["terms"])
        for name, info in data["inputs"].items()
    }
    out_data = data["output"]
    output = Variable(out_data["universe"], out_data["terms"])
    rules = [Rule(r["if"], r["then"]) for r in data["rules"]]

    return KnowledgeBase(
        description=data.get("description", ""),
        inputs=inputs,
        output_name=out_data["name"],
        output=output,
        rules=rules,
        default_inputs=data.get("default_inputs", {}),
    )