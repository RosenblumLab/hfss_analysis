from dataclasses import dataclass
from typing import Iterable, Union


def add_units(value: Union[float, int], units: str) -> str:
    """adding units to float/int and returns a str"""
    return f'{value}{units}'


@dataclass
class ValuedVariable:
    name: str
    display_name: str
    value: str
    value_float: float


@dataclass
class Variable:
    design_name: str
    iterable: Iterable[float]  # values to sweep
    units: str
    display_name: str = None  # if not given use design name

    def __post_init__(self):
        if self.display_name is None:
            self.display_name = self.design_name

    def gen(self) -> Iterable[ValuedVariable]:
        for value in self.iterable:
            yield ValuedVariable(
                name=self.design_name,
                display_name=self.display_name,
                value=add_units(value, self.units),
                value_float=float(value),
            )