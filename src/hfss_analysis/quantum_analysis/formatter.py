from typing import Dict, Tuple, List, Iterable
import pandas as pd
from itertools import combinations_with_replacement
from ..simulation_basics import SimulationResult


class Constants:
    ANHARMONICITY = 'Anharmonicity'
    COUPLING = 'Coupling'


def _get_chis(data: Dict) -> pd.DataFrame:
    return data['chi_ND']


def _get_frequencies(data: Dict) -> pd.Series:
    return data['f_ND']


def _sequential_mode_to_label(modes_to_labels: Dict[int, str]) -> Dict[int, str]:
    """Simply convet the modes numbers in the dict to sequential array.
    e.g.:
        input:  {0: 'transmon', 2: 'readout', 4: 'cavity'}
        output: {0: 'transmon', 1: 'readout', 2: 'cavity'}
    """
    return {i: modes_to_labels[k] for i, k in enumerate(modes_to_labels.keys())}


def _flatten_chis(chis: pd.DataFrame) -> Dict[Tuple[int, int], float]:
    """
    Assuming the chi matrix is a symmetric matrix, hence we only want 2-combinations
    with replacements
    :param chis: dataframe symmetric matrix NxN
    :param mode_to_label: dictionary of mode number (should be sequential modes) to str
    :return: a dictionary where the keys are the combinations of the modes
    """
    assert chis.shape[0] == chis.shape[1]

    def _helper():
        for i, j in combinations_with_replacement(range(chis.shape[0]), r=2):
            yield (i, j), chis[i][j]

    return {k: v for k, v in _helper()}


def _apply_mode_to_label_on_flatten_chi(flat_chi: Dict[Tuple[int, int], float],
                                        modes_to_labels: Dict[int, str]):

    def _format_key(t: Tuple[int, int]):
        if t[0] == t[1]:
            names = modes_to_labels[t[0]]
            suffix = Constants.ANHARMONICITY
        else:
            names = f'{modes_to_labels[t[0]]} - {modes_to_labels[t[1]]}'
            suffix = Constants.COUPLING
        return f'{names} {suffix} (Mhz)'

    return {_format_key(k): v for k, v in flat_chi.items()}


def _format_frequencies(frequencies: pd.Series, modes_to_labels: Dict[int, str]) -> Dict[str, float]:

    def _format_value(freq: float):
        return freq / 1e3

    def _format_key(s: str):
        return f'{s} ND Freq. (Ghz)'

    return {_format_key(modes_to_labels[i]): _format_value(freq)
            for i, freq in enumerate(frequencies)}


def apply_format_single_dict(data: Dict, modes_to_labels: Dict[int, str]):
    modes_to_labels = _sequential_mode_to_label(modes_to_labels)

    # formatting chis
    chis = _get_chis(data)
    chis = _flatten_chis(chis)
    chis = _apply_mode_to_label_on_flatten_chi(chis, modes_to_labels)

    # formatting frequencies
    frequencies = _get_frequencies(data)
    frequencies = _format_frequencies(frequencies, modes_to_labels)

    # joining them to one dict and return
    return dict(**chis, **frequencies)


def apply_format_dict(data: Iterable[Dict], modes_to_labels: Dict[int, str] = None) -> List[Dict]:
    return list(map(lambda x: apply_format_single_dict(x, modes_to_labels), data))


def apply_format_single(data: SimulationResult, modes_to_labels: Dict[int, str] = None) -> SimulationResult:
    result = data.result
    formatted_result = apply_format_single_dict(result, modes_to_labels)
    snapshot = data.snapshot
    return SimulationResult(result=formatted_result, snapshot=snapshot)


def apply_format(data: List[SimulationResult],
                 modes_to_labels: Dict[int, str] = None) -> List[SimulationResult]:
    return list(map(lambda x: apply_format_single(x, modes_to_labels), data))


