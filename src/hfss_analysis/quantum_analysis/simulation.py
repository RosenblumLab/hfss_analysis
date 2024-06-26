from typing import Dict, List, Optional, Literal
import pyEPR as epr
from ..hfss_project import Project
from ..simulation_basics import SimulationResult
from ..sweep import Sweep


class QuantumSimulation:

    def __init__(self, project: Project, modes: List[int]):
        self.project = project
        self.modes = modes
        self.snapshots = None
        self.variations = None
        self.results = None

    def _clear(self):
        self.results = []
        self.snapshots = []
        self.variations = []

    def _prepare_snapshots_and_variations(self, sweep: Optional[Sweep] = None,
                                          variation_chooser: Literal['all', 'current'] = 'current'):
        if sweep:
            self.snapshots = sweep.snapshots
        elif variation_chooser == 'current':
            self.snapshots = [self.project.get_snapshot()]
        elif variation_chooser == 'all':
            self.snapshots = list(self.project.inverse_variation_dict.keys())
        else:
            raise ValueError

        self.variations = [self.project.inverse_variation_dict[snapshot] for snapshot in self.snapshots]

    def _prepare_quantum_analysis(self) -> epr.QuantumAnalysis:

        data_file, _ = self.project.distributed_analysis.do_EPR_analysis(modes=self.modes,
                                                                         variations=self.variations,
                                                                         append_analysis=False)
        return epr.QuantumAnalysis(data_file)

    def analysis(self, sweep: Optional[Sweep] = None,
                 variation_chooser: Literal['all', 'current'] = 'current') -> List[SimulationResult]:

        self._clear()
        self._prepare_snapshots_and_variations(sweep, variation_chooser)
        results = self._analyze_variations()

        self.results = list(results.values())
        return [SimulationResult(result=result, snapshot=snapshot)
                for snapshot, result in zip(self.snapshots, self.results)]

    def _analyze_variations(self):
        try:
            # preparation of epra
            epra = self._prepare_quantum_analysis()

            # analysis of the given variations
            results = epra.analyze_all_variations(cos_trunc=8, fock_trunc=15,
                                                  # modes=list(range(len(self.modes))),
                                                  variations=self.variations,
                                                  analyze_previous=True)

        except Exception as e:
            raise e

        finally:
            # the analysis modify the expression of all design variables, change them back after done
            self.project.set_depended_variables()

        return results


def analyze(project: Project, modes: List[int], sweep: Optional[Sweep] = None,
            variation_chooser: Literal['all', 'current'] = 'current') -> List[SimulationResult]:
    assert len(project.pinfo.junctions) > 0, "No Josephson junctions were added to the project!"
    sim = QuantumSimulation(project, modes)
    return sim.analysis(sweep, variation_chooser)
