from hfss_analysis.hfss_project.project import Project
from hfss_analysis.variables.variables import ValuedVariable
from typing import Dict, Tuple, Iterable, List
import pyEPR as epr
from pyEPR.core_quantum_analysis import HamiltonianResultsContainer


def prepare(project, modes, variations):
    data_file, _ = project.distributed_analysis.do_EPR_analysis(modes=modes, variations=variations)
    return epr.QuantumAnalysis(data_file)


def quantum_analysis(project: Project, junction_info: Dict[str, Dict[str, str]] = None,
                     modes: List[int] = None,
                     snapshots: Iterable[Tuple[ValuedVariable, ...]] = None) -> HamiltonianResultsContainer:
    # variation number is the ID of the already analyzed simulation
    if not snapshots:
        snapshots = [project.get_all_variables()]

    variations = [project.inverse_variation_dict[snapshot] for snapshot in snapshots]

    # adding junctions
    project.add_junctions(junction_info)

    # preparing quantum analysis
    epra = prepare(project, modes, variations)

    # analysis of the given variations
    return epra.analyze_all_variations(cos_trunc=8, fock_trunc=15, modes=modes, variations=variations)
    # chi_matrix = epra.get_chis()
    # ND_freqs = epra.get_frequencies(numeric=True)
    # return chi_matrix, ND_freqs
