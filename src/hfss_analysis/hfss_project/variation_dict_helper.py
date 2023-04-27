from hfss_analysis.variables.variables import ValuedVariable, round_valued_variable, sort_valued_variables, round_valued_variables
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import re


DEFAULT_FORMATTER = lambda x: x


@dataclass
class Pattern:
    raw: str
    compiled: re.Pattern = field(init=False)
    # match: re.Match = None

    def __post_init__(self):
        self.compiled = re.compile(self.raw)


# VALUE_PATTERN = '(?P<value>[+-]?\d+(?:\.\d+)?)'
VALUE_PATTERN = r'(?P<value>[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?)'
NAME_PATTERN = r'(?P<name>[\w\$_\d]+)'
UNIT_PATTERN = r'(?P<unit>\w*)'
PATTERN_FOR_VARIATION = Pattern(rf"{NAME_PATTERN}='{VALUE_PATTERN}{UNIT_PATTERN}'")


def match_to_valued_variable(match: re.Match) -> Optional[ValuedVariable]:
    data = match.groupdict()
    return dict_to_valued_variable(data)


def dict_to_valued_variable(data: Dict[str, str]) -> Optional[ValuedVariable]:
    name, value, unit = data['name'], data['value'], data['unit']
    try:
        valued_variable = ValuedVariable(
            name=name,
            value=float(value),
            unit=unit
        )
        return round_valued_variable(valued_variable)

    except ValueError:
        print(f'Cannot convert value to float! given {value} for name: {name} and unit {unit}')
        raise ValueError


def text_to_valued_variables(text: str) -> Tuple[ValuedVariable, ...]:
    """string to a tuple of valued variables.
    returns sorted valued variables """
    def _helper():
        for m in PATTERN_FOR_VARIATION.compiled.finditer(text):
            yield match_to_valued_variable(m)

    return sort_valued_variables(_helper())


def dict_to_valued_variables(data: Dict[str, str]) -> Tuple[ValuedVariable, ...]:

    pattern = Pattern(f'{VALUE_PATTERN}{UNIT_PATTERN}')

    def _helper():
        for k, v in data.items():
            m = pattern.compiled.search(v)
            yield dict_to_valued_variable({'name': k,
                                           **m.groupdict()})

    return sort_valued_variables(_helper())


def construct_variables_to_variation(variation_dict: Dict[str, str])\
        -> Dict[Tuple[ValuedVariable, ...], str]:

    # iterating over the variation dict and constructing the keys using text to valued
    # variables. in addition, we make sure that the key does not already exist (otherwise it's not an inverse)
    result = {}
    for variation_number, text in variation_dict.items():
        valued_variables = text_to_valued_variables(text)

        # verify that this valued_variable does not appear in result
        if valued_variables in result:
            print('Cannot construct the variable to variation as the key is not unique!!! collision of '
                  f'{valued_variables}\nMake sure that the names given are the union of all dynamic variables!')
            raise ValueError

        result[valued_variables] = variation_number

    return result


def parameters_to_variation(variation_dict: Dict[str, str],
                            parameters: Tuple[ValuedVariable]):

    valued_vars_to_variation_dict = construct_variables_to_variation(variation_dict)

    # sorting the parameters and rounding
    parameters = round_valued_variables(parameters)
    parameters = sort_valued_variables(parameters)

    return valued_vars_to_variation_dict[parameters]

