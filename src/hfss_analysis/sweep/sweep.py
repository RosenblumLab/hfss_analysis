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
    # results: Dict = field(default_factory=dict)
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

    # def make(self, project: Project, modules_names: Union[str, List[str]], modules_params_dict: Dict[str, Dict]):
    #     # convert modules to list
    #     if isinstance(modules_names, str):
    #         modules_names = [modules_names]
    #
    #     # validate
    #     validate_modules(modules_names)
    #
    #     # iterating over the modules and execute each one of them
    #     for module_name in modules_names:
    #
    #         # getting the relevant parameters
    #         params = modules_params_dict.get(module_name, {})
    #
    #         self._make_single(project, module_name, params)
    #
    #
    # def _make_single(self, project: Project, module_name: str, params: Dict):
    #     # iterate over all parameters
    #
    #     for hfss_parameters in self.make_unify_iterable():
    #
    #         # getting the module
    #         module = SUPPORTED_MODULES[module_name]
    #
    #         # set hfss parameters
    #
    #         # get a snapshot
    #
    #         # execution
    #         result = module(project, **params)
    #
    #         # saving the result in a dict
    #         self.results[module_name] = result


    # def make_classic(self):
    #     # classic analysis
    #     full_var_list = list(self.make_unify_iterable())
    #     for i, variables in (pbar := tqdm(enumerate(full_var_list), total=len(full_var_list))):
    #         pbar.set_description(f'Variation {i}')
    #         # setting & logging all variables
    #         log_info = '\n' + '#' * 20
    #         for var in variables:
    #             self.simulation.project.set_variable(var.name, var.value)
    #             log_info += f'\nSetting {var.display_name}={var.value}'
    #         log_info += '\n' + '#' * 20
    #
    #         epr.logger.info(log_info)
    #
    #         # analysing
    #         self.simulation.analyze_classic()
    #
    #     # extracting all eigenmodes
    #     variation_dict = self.simulation.get_variations_dict()
    #     variation_iter = self.gen_variation_sequence(variation_dict)
    #     # add new attribute to sweep and save iteraton as list
    #     self._variations = list(variation_iter)
    #     self.simulation.extract_all_eigenmodes(variation_iter=self._variations)
    #
    # def make_quantum(self):
    #     # getting chi matrix and numerically-diagonalized (ND) frequencies
    #     self.simulation.make_quantum(variations_iter=self._variations)

    # def make_all(self, do_quantum=True):
    #     # making simulations
    #     self.make_classic()
    #
    #     if do_quantum:
    #         self.make_quantum()
    #
    #         # getting results
    #         self.results = self.simulation.concat_eigenmodes_chi_and_ND_freqs()
    #
    #     else:
    #         self.results = self.simulation.eigenmodes
    #
    #     # adding parameters
    #     self.add_parameters(self.results)
    #
    #     return self.results
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
