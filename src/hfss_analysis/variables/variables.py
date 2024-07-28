from dataclasses import dataclass
from typing import Iterable, Union, Optional, Tuple, Dict
import numpy as np

ROUNDING_DIGIT = 10


def add_units(value: Union[float, int], units: str) -> str:
    """adding units to float/int and returns a str"""
    return f'{value}{units}'


@dataclass(frozen=True)
class ValuedVariable:
    name: str
    value: float
    unit: str

    def to_name_and_value(self) -> Tuple[str, str]:
        return self.name, add_units(self.value, self.unit)


def round_valued_variable(valued_var: ValuedVariable) -> ValuedVariable:
    return ValuedVariable(
        name=valued_var.name,
        value=np.round(valued_var.value, decimals=ROUNDING_DIGIT),
        unit=valued_var.unit
    )


@dataclass
class Variable:
    name: str
    iterable: Iterable[float]  # values to sweep
    units: str

    # display_name: str = None  # if not given use design name

    # def __post_init__(self):
    #     if self.display_name is None:
    #         self.display_name = self.design_name

    def gen(self) -> Iterable[ValuedVariable]:
        for value in self.iterable:
            v = ValuedVariable(
                name=self.name,
                value=value,
                unit=self.units,
            )
            yield round_valued_variable(v)


def sort_valued_variables(valued_vars: Iterable[ValuedVariable]) -> Tuple[ValuedVariable, ...]:
    return tuple(sorted(valued_vars, key=lambda x: x.name))


def round_valued_variables(valued_vars: Iterable[ValuedVariable]) -> Iterable[ValuedVariable]:
    return map(round_valued_variable, valued_vars)


def round_and_sort_valued_variables(valued_vars: Iterable[ValuedVariable]) -> Tuple[ValuedVariable, ...]:
    return sort_valued_variables(round_valued_variables(valued_vars))


def snapshot_to_dict(snapshot: Tuple[ValuedVariable, ...]) -> Dict[str, float]:
    return {f'{v.name} ({v.unit})': v.value for v in snapshot}

# def sort_and_round_valued_vars(valued_vars: Iterable[ValuedVariable]) -> Tuple[ValuedVariable, ...]:
#     return sort_valued_variables(round_valued_variables(valued_vars))
