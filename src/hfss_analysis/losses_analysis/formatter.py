from ..simulation_basics import SimulationResult
from typing import Dict, Tuple, List
from functools import reduce


# TODO unify with the classical_simulation formatter

def _convert_modes_to_labels(data: Dict, modes_to_labels: Dict[int, str]):
    """For each mode in the mapping we replace the data with its name.
    Also removes any mode that do not appear in the `modes_to_labels` mapping.
    """
    result = {}
    for k, v in data.items():
        result[k] = {label: v[mode] for mode, label in modes_to_labels.items()}
    return result


def _flatten(data: Dict):
    def _helper():
        for title, title_data in data.items():
            yield {f'{mode_name} {title}': value for mode_name, value in title_data.items()}
    return reduce(lambda x, y: dict(**x, **y), _helper())


def _sort_dict(data: Dict):
    return {k: data[k] for k in sorted(data.keys())}


def apply_format_single_dict(data: Dict, modes_to_labels: Dict[int, str] = None) -> Dict:
    if modes_to_labels:
        data = _convert_modes_to_labels(data, modes_to_labels)
    data = _flatten(data)
    return _sort_dict(data)


def apply_format_dict(data: List[Dict], modes_to_labels: Dict[int, str] = None) -> List[Dict]:
    return list(map(lambda x: apply_format_single_dict(x, modes_to_labels), data))


def apply_format_single(data: SimulationResult, modes_to_labels: Dict[int, str] = None) -> SimulationResult:
    result = data.result
    formatted_result = apply_format_single_dict(result, modes_to_labels)
    snapshot = data.snapshot
    return SimulationResult(result=formatted_result, snapshot=snapshot)


def apply_format(data: List[SimulationResult],
                 modes_to_labels: Dict[int, str] = None) -> List[SimulationResult]:
    return list(map(lambda x: apply_format_single(x, modes_to_labels), data))
