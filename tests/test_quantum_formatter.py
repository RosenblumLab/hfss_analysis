import pandas as pd
from hfss_analysis import quantum_analysis


data = {
    'f_ND': pd.Series([1, 2, 3]),
    'chi_ND': pd.DataFrame({0: {0: 100, 1: 1, 2: 3},
                            1: {0: 1, 1: 5, 2: 10},
                            2: {0: 3, 1: 10, 2: 10}})
}

mode_to_label = {0: 'hi', 1: 'bye', 5: 'shalom'}

expected = {
    'hi ND Freq. (Ghz)': 1 * 1e-3,
    'bye ND Freq. (Ghz)': 2 * 1e-3,
    'shalom ND Freq. (Ghz)': 3 * 1e-3,
    'hi - bye Coupling (Mhz)': 1,
    'hi - shalom Coupling (Mhz)': 3,
    'bye - shalom Coupling (Mhz)': 10,
    'hi Anharmonicity (Mhz)': 100,
    'bye Anharmonicity (Mhz)': 5,
    'shalom Anharmonicity (Mhz)': 10,
}


def test_quantum_formatter():
    result = quantum_analysis.apply_format_single_dict(data, mode_to_label)
    assert(result == expected)
