from typing import Optional, Dict, List
from ..sweep import Sweep
from ..hfss_project import Project
from ..simulation_basics import SimulationResult


class ClassicalSimulation:

    def __init__(self, project: Project):
        self.project = project
        # self.sweep = sweep
        self.results = None
        self.snapshots = None
        # self._clear()

    def _clear(self):
        self.results = []
        self.snapshots = []

    def _generate_snapshots(self, sweep: Optional[Sweep] = None):
        if not sweep:
            yield self.project.get_snapshot()
        else:
            yield from sweep.set_parameters_and_yield_snapshot()

    def analysis(self, sweep: Optional[Sweep] = None) -> List[SimulationResult]:
        # clearing memory of snapshots and results
        self._clear()

        for snapshot in self._generate_snapshots(sweep):

            self.snapshots.append(snapshot)

            self.project.analyze()

            # getting results
            self.results.append(self.project.get_analysis_results(snapshot))

        return self._results_to_dict()

    def _results_to_dict(self) -> List[SimulationResult]:
        return [SimulationResult(result=result.to_dict(),
                                 snapshot=snapshot)
                for snapshot, result in zip(self.snapshots, self.results)]


def analyze(project: Project, sweep: Optional[Sweep] = None) -> List[SimulationResult]:
    sim = ClassicalSimulation(project)
    return sim.analysis(sweep)

