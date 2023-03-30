import numpy as np
import pandas as pd
import pyEPR as epr
from itertools import product, combinations
from dataclasses import dataclass, field
from typing import List, Iterable, Union, Dict, Tuple, Optional
import re
from tqdm import tqdm

QF = 'Quality Factor'
FREQ = 'Freq. (GHz)'
LIFETIME = 'Lifetime (us)'
ROUNDING_DIGIT = 4  # Used to adapt HFSS floating point rounding and Python/NumPy rounding


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


def format_ND_freqs(ND_freqs: pd.DataFrame, format_dict: Dict[str, int],
                    variations_iter: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """
    :param ND_freqs: a dataframe with dim of the frequencies received from the numerical diagonalization done in the
        quantum analysis
    :param format_dict: an element to mode dict. e.g.:
            {'cavity': 1,
            'transmon: 0,
            'readout': 2}
    :return: formatted DataFrame
    """
    ordered_elements = [elem[0] for elem in sorted([(elem, num) for elem, num in format_dict.items()],
                                                   key=lambda x: x[1])]

    ND_freqs.columns.name = None
    ND_freqs = ND_freqs.transpose()
    # if variations_iter is None:
        # ND_freqs = ND_freqs.sort_index(key=lambda x: x.to_series().astype(int))
    variations_iter = [str(i) for i in range(len(ND_freqs.index))] if variations_iter is None else variations_iter
    # else:
    ND_freqs = ND_freqs.reindex(variations_iter)
    ND_freqs.columns = [f'Freq ND {element} (MHz)' for element in ordered_elements]
    ND_freqs.index = pd.RangeIndex(stop=len(ND_freqs.index))
    return ND_freqs


def format_all_chis(chi_matrix: pd.DataFrame, format_dict: Dict[str, int],
                    variations_iter: Optional[Iterable[str]] = None) -> pd.DataFrame:
    """
    :param chi_matrix: a dataframe with dim of variations x N x N where N is the length of format_dict
    :param format_dict: an element to mode dict. e.g.:
            {'cavity': 1,
            'transmon: 0,
            'readout': 2}
    :param variations_iter: Used by the `Sweep` class to adapt the order of the iteration to the given parameters.
    :return: a dataframe with the length of 2 choose N times variations
    """

    def _helper(variations_iter: Iterable[Union[int, str]]):
        for i in variations_iter:
            chi = chi_matrix.loc[[str(i)]]
            yield format_chi_matrix(chi, format_dict)

    if variations_iter is None:
        variations_num = int(chi_matrix.shape[0] / len(format_dict))  # number of rows in chi div num of elements
        variations_iter = range(variations_num)

    return pd.DataFrame(list(_helper(variations_iter=variations_iter)))


def format_chi_matrix(chi_matrix: pd.DataFrame, format_dict: Dict[str, int]) -> Dict[str, float]:
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
        res[f'{ordered_elements[i]} Anharmonicity (MHz)'] = anharmonicity[i]
        res[f'{coupling_names[i]} (MHz)'] = couplings[i]
    return res


def do_quantum_analysis(pinfo, modes):
    eprh = epr.DistributedAnalysis(pinfo)
    eprh.do_EPR_analysis(modes=modes)
    epra = epr.QuantumAnalysis(eprh.data_filename)
    epra.analyze_all_variations(cos_trunc=8, fock_trunc=15, modes=modes)
    chi_matrix = epra.get_chis()
    ND_freqs = epra.get_frequencies(numeric=True)
    return chi_matrix, ND_freqs


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

    def get_setup(self, setup_name: str) -> epr.ansys.HfssSetup:
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
    ND_freqs: pd.DataFrame = field(default_factory=pd.DataFrame)  # Frequencies from numerical diagonalization

    def __post_init__(self):
        # check the validity of the format dict
        if self.format_dict is None:
            self.format_dict = {f'Mode {i}': i for i in range(3)}

    def clear(self):
        self.eigenmodes = pd.DataFrame()
        self.chi_matrix = pd.DataFrame()
        self.ND_freqs = pd.DataFrame()

    def analyze_classic(self):
        # analysing
        setup = self.project.get_setup(self.setup_name)
        if setup.basis_order != '-1':
            epr.logger.warning('Setup order is not set to "Mixed Order", which usually gives the best results.')

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

    def make_classic(self) -> pd.DataFrame:
        # analysing
        self.analyze_classic()

        # saving results
        self.extract_all_eigenmodes()

        return self.eigenmodes

    def add_junctions(self):
        for junction_name, value in self.junctions.items():
            self.project.pinfo.junctions[junction_name] = value
        self.project.pinfo.validate_junction_info()

    def make_quantum(self, variations_iter: Optional[Iterable[str]] = None):
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

        # make analysis and get chi matrix
        chi_matrix, ND_freqs = do_quantum_analysis(self.project.pinfo, modes)

        # formatting chi matrix and ND frequencies to fit format dict
        chi_matrix = format_all_chis(chi_matrix, self.format_dict, variations_iter=variations_iter)
        ND_freqs = format_ND_freqs(ND_freqs, self.format_dict, variations_iter=variations_iter)

        # adding them to the results
        self.chi_matrix = pd.concat([self.chi_matrix, chi_matrix])
        self.ND_freqs = pd.concat([self.ND_freqs, ND_freqs])

    def concat_eigenmodes_chi_and_ND_freqs(self):
        # parsing eigenmodes according to the format dict
        return pd.concat([self.ND_freqs, self.chi_matrix, self.eigenmodes], axis=1)

    def make_all(self):
        self.make_classic()
        self.make_quantum()
        return self.concat_eigenmodes_chi_and_ND_freqs()


def gen_var_values(s, pattern_lst):
    for p in pattern_lst:
        m = p.search(s)
        if not m:
            yield None
        var_name, value, unit = m.groups()
        yield np.round(float(value), decimals=ROUNDING_DIGIT)


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

    def _helper(pattern_lst):
        for k, v in variations_dict.items():
            constructed_key = tuple(gen_var_values(v, pattern_lst))
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
    _variations: List[str] = None  # Reorganize the variations according to the given parameters

    def gen_variation_sequence(self, variation_dict):
        mem = {}
        for vars in self.make_unify_iterable():
            var_names = tuple(map(lambda x: x.name, vars))
            var_values = tuple(map(lambda x: np.round(x.value_float, decimals=ROUNDING_DIGIT), vars))
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
        self.results = pd.concat([parameters_df, df], axis=1)

    def make_classic(self):
        # classic analysis
        full_var_list = list(self.make_unify_iterable())
        for i, variables in (pbar := tqdm(enumerate(full_var_list), total=len(full_var_list))):
            pbar.set_description(f'Variation {i}')
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
        # add new attribute to sweep and save iteraton as list
        self._variations = list(variation_iter)
        self.simulation.extract_all_eigenmodes(variation_iter=self._variations)

    def make_quantum(self):
        # getting chi matrix and numerically-diagonalized (ND) frequencies
        self.simulation.make_quantum(variations_iter=self._variations)

    def make_all(self, do_quantum=True):
        # making simulations
        self.make_classic()

        if do_quantum:
            self.make_quantum()

            # getting results
            self.results = self.simulation.concat_eigenmodes_chi_and_ND_freqs()

        else:
            self.results = self.simulation.eigenmodes

        # adding parameters
        self.add_parameters(self.results)

        return self.results

    def make_unify_iterable(self) -> Iterable:
        """Convert the variables to a single iterable"""
        iter_lst = [variable.gen() for variable in self.variables]
        if self.strategy == 'product':
            return product(*iter_lst)
        if self.strategy == 'zip':
            return zip(*iter_lst)
