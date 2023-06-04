from dataclasses import dataclass, asdict
from typing import Any, Tuple, Dict, List, Iterator
from ..variables.variables import ValuedVariable, snapshot_to_dict
from collections import defaultdict
from functools import reduce
import json
from pathlib import Path


@dataclass
class SimulationResult:
    result: Dict[str, Any]
    snapshot: Tuple[ValuedVariable, ...]

    def to_dict(self, with_snapshot: bool = True):
        if with_snapshot:
            return asdict(self)
        else:
            return self.result

    def to_flat_dict(self):
        return _merge_two_dicts(self.result, snapshot_to_dict(self.snapshot))

    def save_to_json(self, path: Path | str, with_snapshot: bool = True):
        with open(Path(path).with_suffix('.json'), 'w') as json_file:
            json.dump(self.to_dict(with_snapshot=with_snapshot), json_file, indent=4)


def _merge_two_dicts(dict_a: Dict, dict_b: Dict):
    return dict(**dict_a, **dict_b)


def _merge_dicts(*dicts: Dict):
    return reduce(_merge_two_dicts, dicts)


def merge(sim_a: SimulationResult, sim_b: SimulationResult) -> SimulationResult:
    """Combine two simulation results with the same snapshot"""
    if sim_a.snapshot != sim_b.snapshot:
        raise ValueError('Cannot merge two simulation results with different snapshots!')

    return SimulationResult(
        snapshot=sim_a.snapshot,
        result=_merge_two_dicts(sim_a.result, sim_b.result)
    )


def flatten_lists_into_generator(lst: list[SimulationResult | list[SimulationResult]]
                                 ) -> Iterator[SimulationResult]:
    for x in lst:
        if isinstance(x, list):
            yield from flatten_lists_into_generator(x)
        else:
            yield x


def join(*sims: List[SimulationResult] | List[List[SimulationResult]] | Tuple[SimulationResult, ...]
         ) -> List[SimulationResult]:
    """A list of results with non-unique snapshots are combined accordingly to their snapshot.

    The function also supports the SimulationResults being passed individually.
    e.g.:
    input:
        results[0] = SimulationResult(  result={'name': 'hi'},          snapshot=(v_a, v_b) )
        results[1] = SimulationResult(  result={'is_horse': True},      snapshot=(v_a, v_b) )
        results[2] = SimulationResult(  result={'is_not_horse': False}, snapshot=(v_a, v_b) )
        results[3] = SimulationResult(  result={'who_am_i': 'hi'},      snapshot=(v_a, v_c) )
    output:
        results[0] = SimulationResult(  result={'name': 'hi', 'is_horse': True, 'is_not_horse': False},
                                        snapshot=(v_a, v_b)
        results[1] = SimulationResult(  result={'who_am_i': 'hi'},
                                        snapshot=(v_a, v_c)

    """
    # Support both methods to pass multiple SimulationResults
    if len(sims) == 1 and isinstance(sims[0], list):
        # Handle case where a single list is passed as the argument
        sims_list = sims[0]
    else:
        # Handle case where multiple arguments are passed individually
        sims_list = list(sims)

    # convert the list to dict
    data = defaultdict(list)

    # flatten the list into a single generator of `SimulationResult` (useful for, e.g., nested list)
    sims_list = flatten_lists_into_generator(sims_list)

    for sim in sims_list:
        data[sim.snapshot].append(sim.result)  # type: ignore

    return [SimulationResult(snapshot=snapshot,  # type: ignore
                             result=reduce(_merge_dicts, results)) for snapshot, results in data.items()]
