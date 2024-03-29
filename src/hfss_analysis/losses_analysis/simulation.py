"""
Module to calculate quality factors that are the result of different loss channels.

Supported loss channels:
    1. Seam loss.
    2. Geometry (G-) and Filling (F-) factors. Note that these values are NOT quality factors.
    3. Surface losses (at the interfaces between metal, substrate and air).
    4. Bulk loss (e.g. from chip substrate)

    TODO add external coupling quality factors.
"""

from typing import List, Optional, Literal, Tuple
from pyEPR.core_distributed_analysis import CalcObject
from ..hfss_project import Project
from ..simulation_basics import SimulationResult
from ..sweep import Sweep
from ..variables.variables import ValuedVariable
import numpy as np
from scipy.constants import epsilon_0
from tqdm import tqdm


Q_SEAM_LOSS = 'Q seam loss'
G_FACTOR = 'G-factor (Ohm)'
F_FACTOR = 'F-factor'
MODE_VOLUME_MAX = 'Mode volume (cm^3) using maximal field'
MODE_VOLUME_MAGNETIC = 'Mode volume (cm^3) using magnetic field'
Q_SURFACES_LOSS = 'Q surfaces loss'
Q_BULK_LOSS = 'Q bulk loss'


def get_electric_energy_in_volume(calcobject: CalcObject, volume: str) -> float:
    vecE = calcobject.getQty("E").smooth()
    vecD = vecE.times_eps()
    E_squared = vecD.dot(vecE.conj()).real()
    UE = E_squared.integrate_vol(name=volume)
    return UE.evaluate() / 2


class LossSimulation:
    """Calculate and save the quality factors corresponding to different loss mechanisms."""

    def __init__(self, project: Project, modes: Optional[List[int]] = None, volume: str = 'AllObjects'):
        r"""
        :param volume: string with the name of the volume in which the EM field lives in HFSS.
        """
        self.project = project
        self.modes = modes or list(range(int(self.project.setup.n_modes)))
        self.volume = volume
        self.snapshots: Optional[List[Tuple[ValuedVariable, ...]]] = None
        self.variations: Optional[List[str]] = None
        self.results = []

    def _clear(self):
        self.results = []
        self.snapshots = []

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


class SeamLossSimulation(LossSimulation):
    r"""
    Here we use the equation
    .. math::
        \frac{1}{Q_{\text{seam}}} = \frac{L}{G_{\text{seam}}} \left[\frac{\int _{\text{seam}}
        \left| \vec{J}_s \times \hat{l}\right|^{2}dl}{\omega  \int _{\text{total}} \mu_0 \left|\vec{H}\right|^2 dV}
        \right]    = \frac{y_{\text{seam}} }{g_{\text{seam}}}
    See T. Brecht's thesis.
    """

    def __init__(self, project: Project,
                 seam_line: str,
                 g_seam: float = 1e6,
                 coordinate_perp_to_line: Literal['x', 'y', 'z'] = 'z',
                 modes: Optional[List[int]] = None):
        r"""
        :param g_seam: value for the seam conductance. Indium gives more than 1e6.
        :param seam_line: string with the name of the seam line in HFSS.
        :param coordinate_perp_to_line: The coordinate perpendicular to the seam line.
        """
        super().__init__(project, modes)
        self.seam_line = seam_line
        self.g_seam = g_seam
        self.coordinate_perp_to_line = coordinate_perp_to_line

    def analysis(self, sweep: Optional[Sweep] = None,
                 variation_chooser: Literal['all', 'current'] = 'current') -> List[SimulationResult]:

        self._prepare_snapshots_and_variations(sweep=sweep, variation_chooser=variation_chooser)

        for snapshot in self.snapshots:
            self.project.set_variables(snapshot)

            snapshot_results_dict = {}
            for mode in (pbar := tqdm(self.modes)):
                pbar.set_description(f"Calculating seam loss for mode {mode}")
                self.project.distributed_analysis.set_mode(mode)

                omega = 2 * np.pi * self.project.get_analysis_results(snapshot).loc[mode, 'Freq. (GHz)'] * 1e9

                calcobject = CalcObject([], self.project.setup)

                if self.coordinate_perp_to_line == 'x':
                    j_surf = calcobject.getQty("Jsurf").scalar_x().smooth()
                elif self.coordinate_perp_to_line == 'y':
                    j_surf = calcobject.getQty("Jsurf").scalar_y().smooth()
                elif self.coordinate_perp_to_line == 'z':
                    j_surf = calcobject.getQty("Jsurf").scalar_z().smooth()
                else:
                    raise ValueError(f'{self.coordinate_perp_to_line=}')

                # j_surf_conj = j_surf.conj()
                j_surf = j_surf.__mul__(j_surf.conj()).real()
                # j_surf = j_surf.real()
                int_j_surf = j_surf.integrate_line(name=self.seam_line)
                int_j_surf = int_j_surf.evaluate()

                vecH = calcobject.getQty("H").smooth()
                vecB = vecH.times_mu()
                squared_magnetic_field = vecH.dot(vecB.conj()).real()
                UH = squared_magnetic_field.integrate_vol(name=self.volume)
                UH = UH.evaluate()

                y_seam = int_j_surf / (UH * omega)
                print(f'y_seam = {y_seam:.2e} /(Ω*m)')

                Q_seam = self.g_seam / y_seam
                print(f'Q_seam = {Q_seam:.2e}')
                snapshot_results_dict[mode] = Q_seam

            self.results.append(snapshot_results_dict)

        return [SimulationResult(result={Q_SEAM_LOSS: result}, snapshot=snapshot)
                for snapshot, result in zip(self.snapshots, self.results)]


class GeometryAndFillingFactorsSimulation(LossSimulation):
    r"""
    Calculate the geometry (G-) and filling (F-) factors. Also calculates the mode volume in two ways.

    Here we use the equation
    .. math::
        G =\frac{\omega \mu_0}{\lambda p_\text{cond}} =
            \omega \mu_0 \frac{\int _{V} \left|{\vec{H}}\right|^2 dv}{\int _{S} \left|{\vec{H}}\right|^2 ds} \ ,
        F = \frac{\int_{V_h}\epsilon_h \left|{\vec{E}}\right|^2 dv}{\int_{V}\epsilon_0 \left|{\vec{E}}\right|^2 dv}
         \approx \frac{t_h \int _{S} \left|{\vec{E}}\right|^2 / (\epsilon_h/\epsilon_0) ds}
         {\int _{V}  \left|{\vec{E}}\right|^2 dv}

    Typical values $\epsilon_r = 33$ and $t_h = 5 \ nm$ dielectric thickness were used in
    https://journals.aps.org/prl/pdf/10.1103/PhysRevLett.119.264801, yielding F~3e-9, or even 1.2e-8 in
    https://link.aps.org/doi/10.1103/PhysRevApplied.13.034032.
    The nominator integral of the filling factor is divided by the relative permittivity since the electric field
        ($\vec{E}$) there is perpendicular to the vacuum-metal interface and hence smaller by that factor.
    See https://phys.libretexts.org/Bookshelves/Electricity_and_Magnetism/Book%3A_Electricity_and_Magnetism_(Tatum
    )/05%3A_Capacitors/5.14%3A__Mixed_Dielectrics.

    For the mode volume we use methods 2 and 3 from
        https://optics.ansys.com/hc/en-us/articles/360034395374-Calculating-the-modal-volume-of-a-cavity-mode.
    """

    def __init__(self, project: Project,
                 epsilon_r: float = 33, t_h: float = 5e-9,
                 modes: Optional[List[int]] = None):
        r"""
        :param epsilon_r: relative permittivity of the dielectrics covering the surface.
        :param t_h: thickness of the dielectrics covering the surface.

        :return factors: a list with the G and F factors of the modes, alternately.
        """
        super().__init__(project, modes)
        self.epsilon_r = epsilon_r
        self.t_h = t_h

    def analysis(self, sweep: Optional[Sweep] = None,
                 variation_chooser: Literal['all', 'current'] = 'current') -> List[SimulationResult]:

        self._prepare_snapshots_and_variations(sweep=sweep, variation_chooser=variation_chooser)

        for snapshot in self.snapshots:
            self.project.set_variables(snapshot)

            snapshot_results_dict = {G_FACTOR: {}, F_FACTOR: {}, MODE_VOLUME_MAX: {}, MODE_VOLUME_MAGNETIC: {}}
            for mode in (pbar := tqdm(self.modes)):
                pbar.set_description(f'Calculating G- and F-factors for mode {mode}')
                self.project.distributed_analysis.set_mode(mode)

                omega = 2 * np.pi * self.project.get_analysis_results(snapshot).loc[mode, 'Freq. (GHz)'] * 1e9

                calcobject = CalcObject([], self.project.setup)

                # G Factor
                vecH = calcobject.getQty("H").smooth()
                vecB = vecH.times_mu()
                squared_magnetic_field = vecH.dot(vecB.conj()).real()
                UH_total = squared_magnetic_field.integrate_vol(name=self.volume).evaluate() * 0.5

                H_surface = vecH.dot(vecH.conj()).real().integrate_surf(name=self.volume)
                H_surface = H_surface.evaluate() * 0.5
                G = omega * (UH_total / H_surface)
                print(f'Geometry factor, G = {G:.2f} Ω')
                snapshot_results_dict[G_FACTOR][mode] = G

                # F Factor
                UE_total = get_electric_energy_in_volume(calcobject=calcobject, volume=self.volume)
                assert np.allclose(UE_total, UH_total, rtol=0.01)
                vecE = calcobject.getQty("E").smooth()
                vecD = vecE.times_eps()
                E_squared = vecE.dot(vecD.conj()).real()
                E_surface = E_squared.integrate_surf(name=self.volume).evaluate() / self.epsilon_r
                UE_surface = 0.5 * self.t_h * E_surface
                F = UE_surface / UE_total
                print(f'Filling factor, F = {F:.3}')
                snapshot_results_dict[F_FACTOR][mode] = F

                # mode volume - total energy divided by its maximum
                max_field = E_squared.maximum_vol(name=self.volume)
                max_energy_value = max_field.evaluate() / 2  # Convert to energy
                mode_volume = (UE_total / max_energy_value) * 1e6  # to cm^3
                print(f'Mode volume using max amplitude method = {mode_volume:.3} cm^3')
                snapshot_results_dict[MODE_VOLUME_MAX][mode] = mode_volume

                # mode volume - (total magnetic energy)^2 divided total(magnetic energy squared)
                squared_magnetic_field = vecH.dot(vecB.conj()).real()
                total_squared_magnetic_field = squared_magnetic_field.integrate_vol(name=self.volume).evaluate()
                total_quadrupled_magnetic_field = (squared_magnetic_field * squared_magnetic_field).integrate_vol(
                    name=self.volume).evaluate()
                mode_volume = ((total_squared_magnetic_field ** 2) / total_quadrupled_magnetic_field) * 1e6  # to cm^3
                print(f'Mode volume using magnetic field method = {mode_volume:.3} cm^3')
                snapshot_results_dict[MODE_VOLUME_MAGNETIC][mode] = mode_volume

            self.results.append(snapshot_results_dict)

        return [SimulationResult(result=result, snapshot=snapshot)
                for snapshot, result in zip(self.snapshots, self.results)]


class SurfaceLossSimulation(LossSimulation):
    r"""
    Calculate the surface losses.
    Here we calculate the surface participation ratios in order to estimate the losses due to them.
    The estimation is a very rough one, unlike the more complex, and probably more accurate, method used in
    https://aip.scitation.org/doi/10.1063/1.4934486 and https://arxiv.org/abs/2206.14334.
    The default values are also taken from the first paper.

    Similar to the calculation of the filling factor in the previous subsection we now calculate the participation
    ratio as
    $$    p_i = \frac{t \int_{S_i} \left| \vec{E} \cdot ( \vec{E}_\bot /\epsilon_r + \vec{E}_\parallel \times
    \epsilon_r) \right| ^{2} ds}{\int _{V} \left|\vec{E}\right| ^2 dv},$$
    where $i$ is the index of the interface over which the integral is done (MA, MS or SA).
    We use the values $\epsilon = 10 \epsilon_0$ and $t=3$ nm.

    The upper bound to the quality factor is then inversely-proportional to this participation ratio, i.e.
    $$ Q_i \leq \frac{1}{p_i \tan \delta_i}.$$
    For that we use upper bounds $\tan \delta_{MS} = 2.6 \times 10^{-3}, \ \tan \delta_{MA} = 2.1 \times 10^{-2}$
    and $\tan \delta_{SA} = 2.2 \times 10^{-3}$.
    """

    def __init__(self, project: Project,
                 metal_surfaces, substrate,
                 epsilon_r: float = 10, t: float = 3e-9,
                 tan_MA=2.1 * 1e-2, tan_MS=2.6 * 1e-3, tan_SA=2.2 * 1e-3,
                 modes: Optional[List[int]] = None):
        r"""
        :param epsilon_r: relative permittivity of the dielectrics covering the surface.
        :param t: thickness of the dielectrics covering the surfaces.
        :param metal_surfaces: list of strings with the names of the metal surfaces on which the dielectrics reside.
        :param substrate: string with the name of the substrate (chip) on which the metal sheets are placed.
        :param tan_MA: Metal-Air interface loss tangent.
        :param tan_MS: Metal-Substrate interface loss tangent.
        :param tan_SA: Substrate-Air interface loss tangent.

        Note that the values for the loss tangents are *upper bounds*
            according to the reference mentioned above, Supplementary Material B.III.

        :return:
        """
        super().__init__(project, modes)
        self.metal_surfaces = metal_surfaces
        self.substrate = substrate
        self.epsilon_r = epsilon_r
        self.t = t
        self.tan_MA = tan_MA
        self.tan_MS = tan_MS
        self.tan_SA = tan_SA

    def analysis(self, sweep: Optional[Sweep] = None,
                 variation_chooser: Literal['all', 'current'] = 'current') -> List[SimulationResult]:

        self._prepare_snapshots_and_variations(sweep=sweep, variation_chooser=variation_chooser)

        for snapshot in self.snapshots:
            self.project.set_variables(snapshot)

            snapshot_results_dict = {}
            for mode in (pbar := tqdm(self.modes)):
                pbar.set_description(f'Calculating surface losses for mode {mode}')
                self.project.distributed_analysis.set_mode(mode)

                calcobject = CalcObject([], self.project.setup)

                UE_total = get_electric_energy_in_volume(calcobject=calcobject, volume=self.volume)
                vecE = calcobject.getQty("E").smooth()

                # MA/MS participation ratio
                E_surface_metal = 0
                for metal_surface in self.metal_surfaces:
                    # normal to surface
                    vecE_normal = vecE.normal2surface(metal_surface)
                    vecD_normal = vecE_normal.__mul__(epsilon_0 / self.epsilon_r)
                    E_squared = (vecE_normal.dot(vecD_normal.conj())).real()
                    E_surface_metal += E_squared.integrate_surf(name=metal_surface).evaluate() / 2

                    # tangent to surface
                    vecE_tangent = vecE.tangent2surface(metal_surface)
                    vecD_tangent = vecE_tangent.__mul__(self.epsilon_r * epsilon_0)
                    E_squared = (vecE_tangent.dot(vecD_tangent.conj())).real()
                    E_surface_metal += E_squared.integrate_surf(name=metal_surface).evaluate() / 2

                p_metal = (self.t * E_surface_metal) / UE_total
                print(f'Metal-Air/Metal-Substrate participation ratio, p_MA = p_MS = {p_metal:.3}')

                # SA participation ratio
                vecE_normal = vecE.normal2surface(self.substrate).__mul__(epsilon_0 / self.epsilon_r)
                vecD_normal = vecE.normal2surface(self.substrate)
                vecE_tangent = vecE.tangent2surface(self.substrate)
                vecD_tangent = vecE.tangent2surface(self.substrate).__mul__(epsilon_0 * self.epsilon_r)
                E_squared = ((vecE_normal.dot(vecD_normal.conj())).__add__(
                    (vecE_tangent.dot(vecD_tangent.conj())))).real()
                E_surface = E_squared.integrate_surf(name=self.substrate).evaluate() / 2
                E_surface_substrate = E_surface - E_surface_metal

                p_SA = (self.t * E_surface_substrate) / UE_total
                print(f'Air-Substrate participation ratio, p_SA = {p_SA:.3}')

                # upper bounds
                Q_MA = 1 / (p_metal * self.tan_MA)
                Q_MS = 1 / (p_metal * self.tan_MS)
                Q_SA = 1 / (p_SA * self.tan_SA)
                Q_surface_total = 1 / (1 / Q_MA + 1 / Q_MS + 1 / Q_SA)

                print(f'Quality factor due to MA loss = {Q_MA:.3}')
                print(f'Quality factor due to MS loss = {Q_MS:.3}')
                print(f'Quality factor due to SA loss = {Q_SA:.3}')
                print(f'Quality factor due to all surface losses = {Q_surface_total:.3}')

                snapshot_results_dict[mode] = Q_surface_total

            self.results.append(snapshot_results_dict)

        return [SimulationResult(result={Q_SURFACES_LOSS: result}, snapshot=snapshot)
                for snapshot, result in zip(self.snapshots, self.results)]


class BulkLossSimulation(LossSimulation):
    r"""
        Calculate the bulk loss caused from a volume (usually the chip substrate).
        * Notice that the relative permittivity of the bulk should be defined in HFSS!

        See https://arxiv.org/abs/2206.14334 for details and a measured value for EFG sapphire loss tangent (62e-9).
    """

    def __init__(self, project: Project,
                 bulk: str, loss_tangent: float,
                 modes: Optional[List[int]] = None):
        r"""
        :param bulk: string with the name of the bulk (usually the chip substrate) in which the losses occur.
        :param loss_tangent: the loss tangent of the bulk.
        """
        super().__init__(project, modes)
        self.bulk = bulk
        self.loss_tangent = loss_tangent

    def analysis(self, sweep: Optional[Sweep] = None,
                 variation_chooser: Literal['all', 'current'] = 'current') -> List[SimulationResult]:

        self._prepare_snapshots_and_variations(sweep=sweep, variation_chooser=variation_chooser)

        for snapshot in self.snapshots:
            self.project.set_variables(snapshot)

            snapshot_results_dict = {}
            for mode in (pbar := tqdm(self.modes)):
                pbar.set_description(f'Calculating bulk loss for mode {mode}')
                self.project.distributed_analysis.set_mode(mode)

                calcobject = CalcObject([], self.project.setup)

                total_UE = get_electric_energy_in_volume(calcobject=calcobject, volume=self.volume)
                bulk_UE = get_electric_energy_in_volume(calcobject=calcobject, volume=self.bulk)
                p_bulk = bulk_UE / total_UE

                bulk_Q_factor = 1 / (p_bulk * self.loss_tangent)

                print(f'Quality factor of mode {mode} due to bulk loss in {self.bulk} = {bulk_Q_factor:.2g}')
                snapshot_results_dict[mode] = bulk_Q_factor

            self.results.append(snapshot_results_dict)

        return [SimulationResult(result={Q_BULK_LOSS: result}, snapshot=snapshot)
                for snapshot, result in zip(self.snapshots, self.results)]


def analyze_seam_loss(project: Project,
                      seam_line: str,
                      g_seam: float = 1e6,
                      coordinate_perp_to_line: Literal['x', 'y', 'z'] = 'z',
                      modes: Optional[List[int]] = None, sweep: Optional[Sweep] = None,
                      variation_chooser: Literal['all', 'current'] = 'current') -> List[SimulationResult]:

    sim = SeamLossSimulation(project=project, modes=modes, seam_line=seam_line, g_seam=g_seam,
                             coordinate_perp_to_line=coordinate_perp_to_line)
    return sim.analysis(sweep, variation_chooser)


def analyze_geometry_and_filling_factors(project: Project,
                                         epsilon_r: float = 33, t_h: float = 5e-9,
                                         modes: Optional[List[int]] = None, sweep: Optional[Sweep] = None,
                                         variation_chooser: Literal['all', 'current'] = 'current'
                                         ) -> List[SimulationResult]:

    sim = GeometryAndFillingFactorsSimulation(project=project, modes=modes, epsilon_r=epsilon_r, t_h=t_h)
    return sim.analysis(sweep, variation_chooser)


def analyze_surface_loss(project: Project,
                         metal_surfaces, substrate,
                         epsilon_r: float = 10, t: float = 3e-9,
                         tan_MA=2.1 * 1e-2, tan_MS=2.6 * 1e-3, tan_SA=2.2 * 1e-3,
                         modes: Optional[List[int]] = None, sweep: Optional[Sweep] = None,
                         variation_chooser: Literal['all', 'current'] = 'current'
                         ) -> List[SimulationResult]:
    sim = SurfaceLossSimulation(project=project, modes=modes,
                                metal_surfaces=metal_surfaces, substrate=substrate,
                                epsilon_r=epsilon_r, t=t,
                                tan_MA=tan_MA, tan_MS=tan_MS, tan_SA=tan_SA)
    return sim.analysis(sweep, variation_chooser)


def analyze_bulk_loss(project: Project,
                      bulk: str, loss_tangent: float,
                      modes: Optional[List[int]] = None, sweep: Optional[Sweep] = None,
                      variation_chooser: Literal['all', 'current'] = 'current'
                      ) -> List[SimulationResult]:
    sim = BulkLossSimulation(project=project, modes=modes,
                             bulk=bulk, loss_tangent=loss_tangent)
    return sim.analysis(sweep, variation_chooser)
