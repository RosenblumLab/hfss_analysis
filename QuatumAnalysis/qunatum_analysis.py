import numpy as np
import pandas as pd
import pyEPR as epr
from itertools import product, combinations
from dataclasses import dataclass, field
from typing import List, Iterable, Union, Dict, Tuple

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


def parse_eigenmodes_results(df: pd.DataFrame, format_dict: Dict[str, int], variation: int) -> pd.DataFrame:
    """ Format the eigenmode results to be compatible with format dict """
    data = df.to_dict()
    res = {}
    for name, mode in format_dict.items():
        res.update(extract_info(data, name, mode))
    return pd.DataFrame(res, index=[variation])


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
                value=add_units(value, self.units)
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

    def extract_all_eigenmodes(self):
        eprh = epr.DistributedAnalysis(self.project.pinfo)
        for variation_num in sorted(eprh.variations, key=lambda x: int(x)):
            # getting frequencies
            df = eprh.get_freqs_bare_pd(variation_num)

            # formatting them
            if self.format_dict is not None:
                df = parse_eigenmodes_results(df, self.format_dict, int(variation_num))

            # adding them to the results
            self.eigenmodes = pd.concat([self.eigenmodes, df])

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


@dataclass
class Sweep:
    simulation: Simulation
    variables: Union[Tuple[Variable], List[Variable]]
    strategy: str = 'product'
    results: pd.DataFrame = None

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
        self.simulation.extract_all_eigenmodes()

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

