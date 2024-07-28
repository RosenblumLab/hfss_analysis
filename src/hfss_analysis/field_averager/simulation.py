from typing import Dict, List, Optional, Literal
from ..hfss_project import Project
from ..simulation_basics import SimulationResult
from ..sweep import Sweep
from pyEPR.ansys import CalcObject, ConstantCalcObject

COMPONENT_NAME_TO_SCALAR = {
    'x': lambda x: x.scalar_x(),
    'y': lambda x: x.scalar_y(),
    'z': lambda x: x.scalar_z()
}

# NAME_FORMATTER = lambda x: f'Avg.  Field ({x})'


def field_name_formatter(field_type: Literal['E', 'H'], component: Literal['x', 'y', 'z']):
    return f'Avg. {field_type} Field ({component})'


class FieldCalculator:

    def __init__(self, project: Project):
        self.project = project

    def _prepare_snapshots(self, sweep: Optional[Sweep] = None,
                           variation_chooser: Literal['all', 'current'] = 'current'):
        if sweep:
            return sweep.snapshots
        elif variation_chooser == 'current':
            return [self.project.get_snapshot()]
        elif variation_chooser == 'all':
            return list(self.project.inverse_variation_dict.keys())
        else:
            raise ValueError

    def _construct_calc_obj(self):
        return CalcObject([], self.project.setup)

    def _calculate_volume(self, volume_name):
        # calculating the volume
        calc_obj = ConstantCalcObject(1, self.project.setup)
        return calc_obj.integrate_vol(volume_name).evaluate()

    def _calculate_field_components(self, field_type: Literal['E', 'H'],
                                    componenet_name: Literal['x', 'y', 'z'],
                                    volume_name: str):
        calc_obj = CalcObject([], self.project.setup)

        # getting the object
        calc_obj = calc_obj.getQty(field_type).smooth()

        # getting the magnitude of specific direction
        calc_obj = COMPONENT_NAME_TO_SCALAR[componenet_name](calc_obj)
        calc_obj = abs(calc_obj)
        calc_obj = calc_obj.real()

        # integration over the volume
        return calc_obj.integrate_vol(volume_name).evaluate()

    def _calculate_field_given_snapshot(self, field_type: Literal['E', 'H'], volume_name: str,
                                        component_names=('x', 'y', 'z')) -> Dict[str, float]:

        volume = self._calculate_volume(volume_name)
        results = {}

        # computing each component
        for c in component_names:
            field = self._calculate_field_components(field_type, c, volume_name)
            results[field_name_formatter(field_type, c)] = field / volume

        return results

    def _calculate_field(self, field_type: Literal['E', 'H'], volume_name: str,
                         sweep: Optional[Sweep] = None,
                         variation_chooser: Literal['all', 'current'] = 'current'):

        for snapshot in self._prepare_snapshots(sweep, variation_chooser):
            self.project.set_variables(snapshot)

            yield self._calculate_field_given_snapshot(field_type, volume_name), snapshot

    def calculate_field(self, field_type: Literal['E', 'H'], volume_name: str,
                        sweep: Optional[Sweep] = None,
                        variation_chooser: Literal['all', 'current'] = 'current') -> List[SimulationResult]:

        results = self._calculate_field(field_type, volume_name, sweep, variation_chooser)

        return list(map(lambda x: SimulationResult(result=x[0], snapshot=x[1]), results))
