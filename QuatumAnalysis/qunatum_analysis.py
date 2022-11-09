import numpy as np
import pandas as pd
import pyEPR as epr
from itertools import product, combinations
from dataclasses import dataclass, field
from typing import List, Iterable, Union, Dict, Tuple, Optional
import re

QF = 'Quality Factor'
FREQ = 'Freq. (GHz)'
LIFETIME = 'Lifetime (us)'


def add_units(value: Union[float, int], units: str) -> str:
    """adding units to float/int and returns a str"""
    return f'{value}{units}'


def extract_info(data: dict, element_name: str, mode_idx: int) -> Dict[str, float]:
    """
    :param data: dict of eigenmodes result, should have only
    :param element_name: name of mode
    :param mode_idx: mode number
    :return: a dict of one variation
    """
    res = {
        QF: data[QF][mode_idx],
        FREQ: data[FREQ][mode_idx],
        LIFETIME: data[QF][mode_idx] / (2 * np.pi * data[FREQ][mode_idx] * 1e3)
    }

    return {f'{element_name} {key}': value for key, value in res.items()}


def parse_eigenmodes_results(df: pd.DataFrame, format_dict: Dict[str, int]) -> pd.DataFrame:
    """ Format the eigenmode results to be compatible with format dict """
    data = df.to_dict()
    res = {}
    for name, mode in format_dict.items():
        res.update(extract_info(data, name, mode))
    return pd.DataFrame([res])


def format_all_chis(chi_matrix: pd.DataFrame, format_dict: Dict[str, int]):
    """
    :param chi_matrix: a dataframe with dim of variations x N x N where N is the length of format_dict
    :param format_dict: an element to mode dict. e.g.:
            {'cavity': 1,
            'transmon: 0,
            'readout': 2}
    :return: a dict with the length of 2 choose N times variations
    """

    def _helper():
        variations = int(chi_matrix.shape[0] / len(format_dict))  # number of rows in chi div num of elements
        for i in range(variations):
            chi = chi_matrix.loc[[str(i)]]
            yield format_chi_matrix(chi, format_dict)

    return pd.DataFrame(list(_helper()))


def format_chi_matrix(chi_matrix: pd.DataFrame, format_dict: Dict[str, int]):
    """
    :param chi_matrix: a dataframe with dim of NxN where N is the length of format_dict
    :param format_dict: an element to mode dict. e.g.:
            {'cavity': 1,
            'transmon: 0,
            'readout': 2}
    :return: a dict with the length of 2 choose N
    """
    ordered_elements = [elem[0] for elem in sorted([(elem, num) for elem, num in format_dict.items()],
                                                   key=lambda x: x[1])]
    anharmonicity = np.diag(chi_matrix)
    element_num = len(format_dict)
    chis_idx = list(combinations(range(element_num), 2))
    couplings = [chi_matrix[i][j] for i, j in chis_idx]
    coupling_names = [f'{ordered_elements[i]}-{ordered_elements[j]}' for i, j in chis_idx]
    res = {}
    for i in range(element_num):
        res[f'{ordered_elements[i]} Anharmonicity (Mhz)'] = anharmonicity[i]
        res[f'{coupling_names[i]} (Mhz)'] = couplings[i]
    return res


def do_quantum_analysis(pinfo, modes):
    eprh = epr.DistributedAnalysis(pinfo)
    eprh.do_EPR_analysis(modes=modes)
    epra = epr.QuantumAnalysis(eprh.data_filename)
    epra.analyze_all_variations(cos_trunc=8, fock_trunc=15)
    return epra.get_chis()


@dataclass
class Project:
    project_directory: str
    project_name: str  # file name
    design_name: str
    pinfo: epr.Project_Info = field(init=False)

    def __post_init__(self):
        self.pinfo = epr.Project_Info(project_path=self.project_directory,
                                      project_name=self.project_name,
                                      design_name=self.design_name)

    def get_project(self):
        return self.pinfo.project

    def get_setup(self, setup_name: str):
        return self.pinfo.design.get_setup(setup_name)

    def set_variable(self, name: str, value: str):
        if name.startswith('$'):
            self.pinfo.project.set_variable(name, value)
        else:
            self.pinfo.design.set_variable(name, value)

    def get_variable_value(self, name: str) -> str:
        return self.pinfo.project.get_variable_value(name)

    def delete_all_solutions(self):
        try:
            self.pinfo.design.delete_full_variation()
        except Exception as e:
            print('No solutions found')


@dataclass
class ValuedVariable:
    name: str
    display_name: str
    value: str
    value_float: float


@dataclass
class Variable:
    design_name: str
    iterable: Iterable[float]  # values to sweep
    units: str
    display_name: str = None  # if not given use design name

    def __post_init__(self):
        if self.display_name is None:
            self.display_name = self.design_name

    def gen(self) -> Iterable[ValuedVariable]:
        for value in self.iterable:
            yield ValuedVariable(
                name=self.design_name,
                display_name=self.display_name,
                value=add_units(value, self.units),
                value_float=float(value),
            )


@dataclass
class Simulation:
    project: Project
    setup_name: str
    format_dict: Dict[str, int] = None
    junctions: Dict[str, Dict[str, str]] = None
    eigenmodes: pd.DataFrame = field(default_factory=pd.DataFrame)
    chi_matrix: pd.DataFrame = field(default_factory=pd.DataFrame)

    def __post_init__(self):
        # check the validity of the format dict
        if self.format_dict is None:
            self.format_dict = {f'Mode {i}': i for i in range(3)}

    def clear(self):
        self.eigenmodes = pd.DataFrame()
        self.chi_matrix = pd.DataFrame()

    def analyze_classic(self):
        # analysing
        setup = self.project.get_setup(self.setup_name)
        setup.analyze()

    def get_variations_dict(self):
        return epr.DistributedAnalysis(self.project.pinfo).get_variations()

    def extract_all_eigenmodes(self, variation_iter: Optional[Iterable[str]] = None):
        eprh = epr.DistributedAnalysis(self.project.pinfo)
        variation_iter = eprh.variations if variation_iter is None else variation_iter
        for variation_num in variation_iter:
            # getting frequencies
            df = eprh.get_freqs_bare_pd(variation_num)

            # formatting them
            if self.format_dict is not None:
                df = parse_eigenmodes_results(df, self.format_dict)

            # adding them to the results
            self.eigenmodes = pd.concat([self.eigenmodes, df], ignore_index=True)

    def make_classic(self):
        # analysing
        self.analyze_classic()

        # saving results
        self.extract_all_eigenmodes()

    def add_junctions(self):
        for junction_name, value in self.junctions.items():
            self.project.pinfo.junctions[junction_name] = value
        self.project.pinfo.validate_junction_info()

    def make_quantum(self):
        # first check the validity of the format dict
        if self.format_dict is None:
            raise ValueError('For quantum simulation format_dict is needed!')

        modes = list(self.format_dict.values())

        if len(modes) > 3:
            raise ValueError(f'Support only up to 3 modes for quantum simulation!! Given: {self.format_dict}')

        if self.junctions is None:
            raise ValueError(f'Please supply junctions for quantum analysis')

        # adding junctions
        self.add_junctions()

        # make anaylsis and get chi matrix
        chi_matrix = do_quantum_analysis(self.project.pinfo, modes)

        # formatting chi matrix to fit format dict
        chi_matrix = format_all_chis(chi_matrix, self.format_dict)

        # adding them to the results
        self.chi_matrix = pd.concat([self.chi_matrix, chi_matrix])

    def concat_eigenmodes_and_chi(self):
        # parsing eigenmodes according to the format dict
        return pd.concat([self.eigenmodes, self.chi_matrix], axis=1)

    def make_all(self):
        self.make_classic()
        self.make_quantum()
        return self.concat_eigenmodes_and_chi()


def gen_var_values(s, pattern_lst):
    for p in pattern_lst:
        m = p.search(s)
        if not m:
            yield None
        var_name, value, unit = m.groups()
        yield float(value)


def create_pattern_lst(names: Iterable[str]):
    # replacing $ with \$
    names = [n.replace('$', '\$') for n in names]
    # creating pattern and compiling it
    # pattern matches to <var name>, <value>, <units>
    value_pattern = '([+-]?(?:[0-9]+)(?:\.[0-9]+)?)'
    return [re.compile(rf'({n})=\'{value_pattern}(\w+)\'') for n in names]


def construct_variables_values_to_variation_number(names: Iterable[str], variations_dict) -> Dict[Tuple[float, ...], str]:
    """
    :param names: iterable of the variable names
    :param variations_dict: a dict of <variation number> : <string of all variables with their values>
    :return: a dict of <tuple(v_0, v_1, v_2,...)> : <variation number>. Where v_0, v_1,... are the values of the
            variable names that appear in the variation dict.
    """

    def _helper(plst):
        for k, v in variations_dict.items():
            constructed_key = tuple(gen_var_values(v, plst))
            if None in constructed_key:
                continue
            yield constructed_key, k

    pattern_lst = create_pattern_lst(names)
    return dict(_helper(pattern_lst))


@dataclass
class Sweep:
    simulation: Simulation
    variables: Union[Tuple[Variable], List[Variable]]
    strategy: str = 'product'
    results: pd.DataFrame = None

    def gen_variation_sequence(self, variation_dict):
        mem = {}
        for vars in self.make_unify_iterable():
            var_names = tuple(map(lambda x: x.name, vars))
            var_values = tuple(map(lambda x: x.value_float, vars))
            if not mem.get(var_names):
                mem[var_names] = construct_variables_values_to_variation_number(var_names, variation_dict)
            yield mem.get(var_names).get(var_values)

    def _create_parameters_dataframe(self) -> pd.DataFrame:

        def _parse(variables: Iterable[ValuedVariable]) -> Dict[str, str]:
            return {var.display_name: var.value for var in variables}

        result = [_parse(variables) for variables in self.make_unify_iterable()]
        return pd.DataFrame(result)

    def add_parameters(self, df: pd.DataFrame):
        parameters_df = self._create_parameters_dataframe()
        self.results = pd.concat([df, parameters_df], axis=1)

    def make_classic(self):
        # classic analysis
        for variables in self.make_unify_iterable():

            # setting & logging all variables
            log_info = '\n' + '#' * 20
            for var in variables:
                self.simulation.project.set_variable(var.name, var.value)
                log_info += f'\nSetting {var.display_name}={var.value}'
            log_info += '\n' + '#' * 20

            epr.logger.info(log_info)

            # analysing
            self.simulation.analyze_classic()

        # extracting all eigenmodes
        variation_dict = self.simulation.get_variations_dict()
        variation_iter = self.gen_variation_sequence(variation_dict)
        self.simulation.extract_all_eigenmodes(variation_iter=variation_iter)

    def make_quantum(self):
        # getting chi matrix
        self.simulation.make_quantum()

    def make_all(self, do_quantum=True):
        # making simulations
        self.make_classic()

        if do_quantum:
            self.make_quantum()

            # getting results
            self.results = self.simulation.concat_eigenmodes_and_chi()

        else:
            self.results = self.simulation.eigenmodes

        # adding parameters
        self.add_parameters(self.results)

        return self.results

    def make_unify_iterable(self) -> Iterable:
        """Convert the variables to a one iterable"""
        iter_lst = [variable.gen() for variable in self.variables]
        if self.strategy == 'product':
            return product(*iter_lst)
        if self.strategy == 'zip':
            return zip(*iter_lst)
