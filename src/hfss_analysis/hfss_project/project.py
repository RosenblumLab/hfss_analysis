from dataclasses import dataclass, field
import pandas as pd
import pyEPR as epr
from typing import Dict, Tuple, Union, Iterable
from ..variables.variables import ValuedVariable
from .variation_dict_helper import dict_to_valued_variables, construct_variables_to_variation


@dataclass
class Project:
    project_directory: str
    project_name: str  # file name
    design_name: str
    setup_name: str

    _variation_dict: Dict[str, str] = None  # dict of variation
    # number to a string of all variables
    _inverse_variation_dict: Dict[Tuple[ValuedVariable], str] = None  # dict of tuple of
    # variables to their variation number

    pinfo: epr.Project_Info = field(init=False)
    project: epr.ansys.HfssProject = field(init=False)
    setup: epr.ansys.HfssSetup = field(init=False)
    design: epr.ansys.HfssDesign = field(init=False)
    distributed_analysis: epr.DistributedAnalysis = field(init=False)

    def __post_init__(self):
        self.pinfo = epr.Project_Info(project_path=self.project_directory,
                                      project_name=self.project_name,
                                      design_name=self.design_name)

        self.project = self.pinfo.project
        self.design = self.pinfo.design
        self.setup = self.design.get_setup(self.setup_name)
        self.distributed_analysis = epr.DistributedAnalysis(self.pinfo)

    def set_variable(self, variable: ValuedVariable):
        name, value = variable.to_name_and_value()
        if variable.name.startswith('$'):
            self.project.set_variable(name, value)
        else:
            self.design.set_variable(name, value)

    def set_variables(self, variables: Iterable[ValuedVariable]):
        for v in variables:
            self.set_variable(v)

    def get_variable(self, name: str) -> str:
        if name.startswith('$'):
            return self.project.get_variable_value(name)
        return self.design.get_variable_value(name)

    def delete_all_solutions(self):
        try:
            self.design.delete_full_variation()
        except Exception as e:
            print('No solutions found')

    def get_all_variables(self) -> Tuple[ValuedVariable, ...]:
        project_vars = self.project.get_variables()
        design_vars = self.design.get_variables()
        all_vars_dict = dict(**project_vars, **design_vars)
        # convert dict to list of valued variables
        return dict_to_valued_variables(all_vars_dict)

    def get_snapshot(self) -> Tuple[ValuedVariable, ...]:
        project_vars = self.project.get_variables()
        design_vars = self.design.get_variables()
        all_vars_dict = dict(**project_vars, **design_vars)
        # convert dict to list of valued variables
        return dict_to_valued_variables(all_vars_dict)

    @property
    def variation_dict(self):
        # update the memory of the variation dict
        # if update is needed than set its inverse to empty dict
        # (so it would be evaluated when inverse is called)
        if not self._is_variation_valid():
            self._variation_dict = self.distributed_analysis.get_variations()
            self._inverse_variation_dict = {}

        return self._variation_dict

    def _is_variation_valid(self) -> bool:
        if (not self._variation_dict) or \
                (self.distributed_analysis.get_variations() == self._variation_dict):
            return False
        return True

    @property
    def inverse_variation_dict(self):
        if (not self._is_variation_valid()) or (not self._inverse_variation_dict):
            variation_dict = self.variation_dict
            self._inverse_variation_dict = construct_variables_to_variation(variation_dict)

        return self._inverse_variation_dict

    def get_analysis_results(self, snapshot: Tuple[ValuedVariable, ...]) -> pd.DataFrame:
        """
        extract results of classical analysis using snapshot
        :param snapshot: a tuple of valued variables used for the analysis
        :return: a dataframe of the frequencies, modes and quality factors
        """
        # snapshot to variation number
        variation_number = self.inverse_variation_dict.get(snapshot)
        if not variation_number:
            print('Cannot find variation number for the given snapshot (tuple of valued vars')
            raise ValueError

        # return frequencies using variation number
        return self.distributed_analysis.get_freqs_bare_pd(variation_number)

    def analyze(self):
        """run hfss analysis based on the current variables """
        if self.setup.basis_order != str(epr.ansys.BASIS_ORDER['Mixed Order']):
            epr.logger.warning('Setup order is not set to "Mixed Order", which usually gives the best results.')

        self.setup.analyze()

    def add_junctions(self, junction_info: Dict[str, Dict[str, str]]):
        for junction_name, value in junction_info.items():
            self.pinfo.junctions[junction_name] = value
        self.pinfo.validate_junction_info()
