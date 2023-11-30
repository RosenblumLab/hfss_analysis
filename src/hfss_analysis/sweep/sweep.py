from dataclasses import dataclass, field
from typing import Tuple, List, Iterable, Union, Dict, Set
import pandas as pd
from itertools import product
from ..hfss_project import Project
from ..variables.variables import ValuedVariable, round_and_sort_valued_variables, Variable


@dataclass
class Sweep:
    project: Project
    variables: Iterable[Variable]
    strategy: str = 'product'
    _snapshots: List[Tuple[ValuedVariable]] = field(default_factory=list)
    _parameters: List[Tuple[ValuedVariable]] = field(default_factory=list)
    dynamic_names: Set = None
    constant_parameters: Dict = field(default_factory=dict)

    def _create_parameters_dataframe(self) -> pd.DataFrame:

        def _parse(variables: Iterable[ValuedVariable]) -> Dict[str, str]:
            return {var.display_name: var.value for var in variables}

        result = [_parse(variables) for variables in self.make_unify_iterable()]
        return pd.DataFrame(result)

    def add_parameters(self, df: pd.DataFrame):
        parameters_df = self._create_parameters_dataframe()
        self.results = pd.concat([parameters_df, df], axis=1)

    def clear(self):
        self._parameters = []
        self._snapshots = []

    def _set_parameters_and_get_snapshot(self, parameters: Tuple[ValuedVariable, ...]):
        # setting the parameters
        self.project.set_variables(parameters)

        # adding the snapshot & returning it
        snapshot = self.project.get_snapshot()
        self._snapshots.append(snapshot)

        return snapshot

    def set_parameters_and_yield_snapshot(self):
        self.clear()
        return map(self._set_parameters_and_get_snapshot,
                   self.parameters)

    @property
    def snapshots(self):
        if not self._snapshots:
            print('Snapshot are not generated yet. Please use the generate snapshot and set parameters')
            raise ValueError
            # self._create_parameters_and_snapshot()
        return self._snapshots

    @property
    def parameters(self):
        if not self._parameters:
            self._parameters = list(map(round_and_sort_valued_variables, self.make_unify_iterable()))
        return self._parameters

    def _create_parameters_and_snapshot(self):
        parameters_set = list(self.make_unify_iterable())
        snapshot = self.project.get_snapshot()
        for params in parameters_set:
            # rounding and sorting
            params = round_and_sort_valued_variables(params)
            # adding to the parameters list
            self._parameters.append(params)

            # getting parameters names
            names = set([p.name for p in params])

            # adding a snapshot of this parameters
            snapshot_without_params = filter(lambda x: x.name not in names, snapshot)
            snapshot = list(params) + list(snapshot_without_params)
            self._snapshots.append(round_and_sort_valued_variables(snapshot))

    def make_unify_iterable(self) -> Iterable:
        """Convert the variables to a single iterable"""
        iter_lst = [variable.gen() for variable in self.variables]
        if self.strategy == 'product':
            return product(*iter_lst)
        if self.strategy == 'zip':
            return zip(*iter_lst)
        print(f'Unknown strategy: {self.strategy}!!!')
        raise ValueError
