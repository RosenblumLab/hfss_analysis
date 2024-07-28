from dataclasses import dataclass, field
import pandas as pd
import pyEPR as epr
from typing import Dict, Tuple, Union, Iterable, Set, Optional
from pathlib import Path
from ..variables.variables import ValuedVariable
from .variation_dict_helper import dict_to_valued_variables, construct_variables_to_variation, text_to_valued_variables


@dataclass
class Project:
    project_directory: Union[str, Path]
    project_name: str  # file name
    design_name: str
    setup_name: str

    # keeps records of variable names that are expression of other variables
    depended_variables: Set[ValuedVariable] = field(init=False)

    _variation_dict: Dict[str, str] = None  # dict of variation
    # number to a string of all variables
    _inverse_variation_dict: Dict[Tuple[ValuedVariable], str] = None  # dict of tuple of
    # variables to their variation number

    pinfo: epr.Project_Info = field(init=False)
    project: epr.ansys.HfssProject = field(init=False)
    setup: epr.ansys.HfssSetup = field(init=False)
    design: epr.ansys.HfssDesign = field(init=False)
    _distributed_analysis: epr.DistributedAnalysis = field(init=False)

    def __post_init__(self):
        self.pinfo = epr.Project_Info(project_path=self.project_directory,
                                      project_name=self.project_name,
                                      design_name=self.design_name)

        self.project = self.pinfo.project
        self.design = self.pinfo.design
        self.setup = self.design.get_setup(self.setup_name)
        self._distributed_analysis = epr.DistributedAnalysis(self.pinfo)

        # finding depended variables
        self.construct_depended_variables()

        # is eigenmode
        self.is_eigenmode: bool = isinstance(self.setup, epr.ansys.HfssEMSetup)

    @property
    def distributed_analysis(self):
        self._distributed_analysis.update_ansys_info()
        return self._distributed_analysis

    def construct_depended_variables(self):
        # getting all variables without any variable
        # that depends on other variables
        all_variables_except_depended = self.get_all_variables()

        # getting all variables
        #   (including variables with expression as their value -
        #   denoted as nominal variables. variable that are depended on
        #   others will be evaluated)
        nominal_variation = self.design.get_nominal_variation()
        all_variables = text_to_valued_variables(nominal_variation)

        # difference of all variables with all variable except depended variables
        # will result in the depended part only
        depended_variables_names = set(map(lambda x: x.name, all_variables)) - \
                                  set(map(lambda x: x.name, all_variables_except_depended))


        # convert names to valued_variable with expression as value (str)
        dicts_of_variables = self._get_all_variables_as_dict()
        depended_dict = {n: dicts_of_variables[n] for n in depended_variables_names}
        depended_variables = tuple(map(lambda x: ValuedVariable(x[0], x[1], ''), depended_dict.items()))
        self.depended_variables = depended_variables


    def set_depended_variables(self):
        self.set_variables(self.depended_variables, check_for_depended=False)

    def set_variable(self, variable: ValuedVariable, check_for_depended: bool = True):
        name, value = variable.to_name_and_value()

        # exclude changing depended variable
        if check_for_depended and \
                (name in set(map(lambda x: x.name, self.depended_variables))):
            return

        if variable.name.startswith('$'):
            self.project.set_variable(name, value)
        else:
            self.design.set_variable(name, value)

    def set_variables(self, variables: Iterable[ValuedVariable], check_for_depended: bool = True):
        for v in variables:
            self.set_variable(v, check_for_depended=check_for_depended)

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
        variable_dict = self._get_all_variables_as_dict()
        # convert dict to list of valued variables
        return dict_to_valued_variables(variable_dict)

    def _get_all_variables_as_dict(self) -> Dict[str, str]:
        project_vars = self.project.get_variables()
        design_vars = self.design.get_variables()
        return dict(**project_vars, **design_vars)


    def get_snapshot(self) -> Tuple[ValuedVariable, ...]:
        # USING NOMINAL
        text = self.design.get_nominal_variation()
        return text_to_valued_variables(text)
        # # Switched back to all variables
        # return self.get_all_variables()

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
        return (self._variation_dict) and \
            (self.distributed_analysis.get_variations() == self._variation_dict)

    @property
    def inverse_variation_dict(self):
        if (not self._is_variation_valid()) or (self._inverse_variation_dict is None):
            variation_dict = self.variation_dict
            self._inverse_variation_dict = construct_variables_to_variation(variation_dict)

        return self._inverse_variation_dict

    def get_analysis_results(self, snapshot: Tuple[ValuedVariable, ...]) -> pd.DataFrame:
        """
        extract results of classical analysis using snapshot
        :param snapshot: a tuple of valued variables used for the analysis
        :return: a dataframe with modes as indices and frequencies and quality factors as columns
        """
        # snapshot to variation number
        variation_number = self.inverse_variation_dict.get(snapshot)
        if not variation_number:
            print('Cannot find variation number for the given snapshot (tuple of valued vars)')
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
