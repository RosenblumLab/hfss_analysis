from hfss_analysis import ValuedVariable
from hfss_analysis.variables.variables import ROUNDING_DIGIT, round_valued_variable
from hfss_analysis.hfss_project.variation_dict_helper import text_to_valued_variables, dict_to_valued_variables

import numpy as np
import pytest


@pytest.mark.parametrize("value", [7.999, 5.66666, 1.2132323, 1.222222, 1.00000001])
def test_rounded_valued_variable(value):
    expected = ValuedVariable(
        value=np.round(value, decimals=ROUNDING_DIGIT),
        name='',
        unit=''
    )

    result = round_valued_variable(
        ValuedVariable(value=value, name='', unit='')
    )

    assert result == expected


@pytest.mark.parametrize("text, expected", [
    ("length='8mm' $hole='11.015000000000001mm'",
     (ValuedVariable('$hole', 11.015, 'mm'), ValuedVariable('length', 8, 'mm'))),

    ("hiho='8' $LLLL='11.015000000000001mm'",
     (ValuedVariable('$LLLL', 11.015, 'mm'), ValuedVariable('hiho', 8, ''))),

    ("  hiho='8'     $LLLL='11.015000000000001mm'     ",
     (ValuedVariable('$LLLL', 11.015, 'mm'), ValuedVariable('hiho', 8, '')))
])
def test_text_to_valued_variables(text, expected):
    result = text_to_valued_variables(text)

    assert result == expected


@pytest.mark.parametrize("data_dict, expected", [
    ({"length": "8mm",  "$hole": "11.015000000000001mm"},
     (ValuedVariable('$hole', 11.015, 'mm'), ValuedVariable('length', 8, 'mm'))),

    ({"hiho": "8", "$LLLL": "11.015000000000001mm"},
     (ValuedVariable('$LLLL', 11.015, 'mm'), ValuedVariable('hiho', 8, ''))),
])
def test_dict_to_valued_variables(data_dict, expected):
    result = dict_to_valued_variables(data_dict)
    assert result == expected

