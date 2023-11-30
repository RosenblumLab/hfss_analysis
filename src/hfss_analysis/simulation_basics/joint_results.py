from dataclasses import dataclass, asdict
from typing import Dict, Tuple, Any, List, Union
from ..variables.variables import ValuedVariable, snapshot_to_dict
from .simulation_result import SimulationResult
import pandas as pd
from pathlib import Path
import json


def json_save(path, data, indent: int = 4):
    s = json.dumps(data)
    with open(path, 'w') as f:
        json.dump(data, f, indent=indent)


def _remove_extention_from_path(path: Path):
    parent = path.parent
    while len(path.suffixes) > 0:
        path = Path(path.stem)
    return parent / path


def _normalize_input_to_path(path_input: Union[str, Path]) -> Path:
    if type(path_input) is str:
        return Path(path_input)
    elif type(path_input) is Path:
        return path_input
    else:
        raise TypeError(f'Expected to get either string or pathlib.Path instance, however got type: '
                        f'{type(path_input)}')

def process_path(path: Union[str, Path]):
    path = _normalize_input_to_path(path)
    path = _remove_extention_from_path(path)
    return path



@dataclass
class JointSimulationResults:
    results: List[SimulationResult]
    constant_variables: Tuple[ValuedVariable, ...]

    def to_dict(self):
        return asdict(self)

    def _pack(self) -> Tuple[List[Dict], Dict]:
        return [r.to_flat_dict() for r in self.results], \
            snapshot_to_dict(self.constant_variables)

    def save_to_csv(self, path: Union[Path, str]):
        # packing data
        data, constants = self._pack()
        # processig path
        path = process_path(path)

        # saving data
        df = pd.DataFrame(data)
        csv_path = Path(path).with_suffix('.csv')
        df.to_csv(csv_path, index=False)

        # saving constants
        json_path = path.parent / Path(f'{path.stem}_constants')
        json_path = json_path.with_suffix('.json')
        json_save(json_path, constants)


def minimize_results(sim_results: List[SimulationResult]) -> JointSimulationResults:
    # asserting that the length of all snapshots is the same
    snapshot_len = len(sim_results[0].snapshot)
    assert all(map(lambda x: len(x.snapshot) == snapshot_len, sim_results))

    # finding the constant variables
    constant_variables = tuple(set.intersection(*[set(r.snapshot) for r in sim_results]))
    constant_variable_names = set(map(lambda x: x.name, constant_variables))

    # finding the dynamic variable names
    all_var_names = set(map(lambda x: x.name, sim_results[0].snapshot))
    dynamic_variable_names = all_var_names - constant_variable_names

    # merging dict of dynamic variables and results
    minimized_results = [SimulationResult(result=sim.result,
                                          snapshot=tuple(filter(lambda x: x.name in dynamic_variable_names,
                                                                sim.snapshot)))
                         for sim in sim_results]

    # return a dict of constants and results with parameters
    return JointSimulationResults(
        results=minimized_results,
        constant_variables=constant_variables
    )
