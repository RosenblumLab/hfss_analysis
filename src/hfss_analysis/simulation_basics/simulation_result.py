from dataclasses import dataclass, asdict
from typing import Any, Tuple, Dict, List
from ..variables.variables import ValuedVariable, snapshot_to_dict
from collections import defaultdict
from functools import reduce


@dataclass
class SimulationResult:
    result: Dict[str, Any]
    snapshot: Tuple[ValuedVariable, ...]

    def to_dict(self):
        return asdict(self)

    def to_flat_dict(self):
        return _merge_two_dicts(self.result, snapshot_to_dict(self.snapshot))


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


def join(sims: List[SimulationResult]) -> List[SimulationResult]:
    """A list of results with non-unique snapshots are combined accordingly to their snapshot
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
    # convert the list to dict
    data = defaultdict(list)
    for sim in sims:
        data[sim.snapshot].append(sim.result)  # type: ignore

    return [SimulationResult(snapshot=snapshot,  # type: ignore
                             result=reduce(_merge_dicts, results)) for snapshot, results in data.items()]







