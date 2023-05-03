from dataclasses import dataclass, asdict
from typing import Dict, Tuple, Any, List
from ..variables.variables import ValuedVariable, snapshot_to_dict
from .simulation_result import SimulationResult
import pandas as pd
from pathlib import Path
import json


def json_save(path, data):
    s = json.dumps(data)
    with open(path, 'w') as f:
        json.dump(data, f)


@dataclass
class JointSimulationResults:
    results: List[SimulationResult]
    constant_variables: Tuple[ValuedVariable, ...]

    def to_dict(self):
        return asdict(self)

    def _pack(self) -> Tuple[List[Dict], Dict]:
        return [r.to_flat_dict() for r in self.results], \
            snapshot_to_dict(self.constant_variables)

    def save_to_csv(self, path):
        data, constants = self._pack()
        # saving data
        df = pd.DataFrame(data)
        df.to_csv(path, index=False)

        # saving constants
        constant_path = f'{Path(path).stem}_constants.json'
        json_save(constant_path, constants)



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
