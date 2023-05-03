"""
Module to calculate quality factors that are the result of different loss channels.

Supported loss channels:
    1. Seam loss
    2. Geometry (G-) and Filling (F-) factors. Note that these values are NOT quality factors.
    3. Surface losses (at the interfaces between metal, substrate and air)
    4. Bulk loss (e.g. from chip substrate)

    TODO add external coupling quality factors.
"""

import numpy as np
import pandas as pd
import pyEPR as epr
# from pyEPR.core import *
from pyEPR.core_distributed_analysis import CalcObject
from deprecated.qunatum_analysis import Simulation
from dataclasses import dataclass, asdict
import logging
from tqdm import tqdm
from typing import Optional, Dict, Union, List, Literal
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
from scipy.constants import epsilon_0

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def get_electric_energy_in_volume(calcobject: CalcObject, volume: str) -> float:
    vecE = calcobject.getQty("E").smooth()
    vecD = vecE.times_eps()
    E_squared = vecD.dot(vecE.conj()).real()
    UE = E_squared.integrate_vol(name=volume)
    return UE.evaluate() / 2


@dataclass
class ModeQualityFactors:
    """Quality factors associated with a specific mode"""
    bare_HFSS: Optional[float] = None
    seam_loss: Optional[float] = None
    surface_losses: Optional[float] = None
    bulk_loss: Optional[float] = None
    coupling_losses: Optional[Dict[str, float]] = None
    G_factor_ohm: Optional[float] = None
    F_factor: Optional[float] = None
    mode_volume_cm3_max_method: Optional[float] = None
    mode_volume_cm3_magnetic_field_method: Optional[float] = None
    
    def to_dict(self):
        d = {}
        for k, v in asdict(self).items():
            if isinstance(v, dict):
                d.update(v)
            elif v is not None:
                d[k] = v
        return d


class QualityFactors:
    def __init__(self, simulation: Simulation, name: str = None):
        if simulation.eigenmodes is None:
            raise ValueError("The simulation must be solved before calculating Q-factors.")
        
        self.eprh = epr.DistributedAnalysis(simulation.project.pinfo)
        self.format_dict: Dict[str, int] = simulation.format_dict
        self.freqs, Qs = self.eprh.get_freqs_bare_pd(variation='0').values.transpose()
        self.quality_factors: Dict[str, ModeQualityFactors] = {mode_name: ModeQualityFactors(bare_HFSS=Qs[mode]) for 
                                                               mode_name, mode in self.format_dict.items()}
        self.name: str = name or simulation.project.design_name

    def calculate_seam_loss(self, seam_line: str, volume: str = 'AllObjects', g_seam: float = 1e6,
                            coordinate_perp_to_line: Literal['x', 'y', 'z'] = 'z'):
        r"""
        Here we use the equation
        .. math::
            \dfrac{1}{Q_{\text{seam}}} = \dfrac{L}{G_{\text{seam}}} \left[\dfrac{\int _{\text{seam}}
            \left| \vec{J}_s \times \hat{l}\right|^{2}dl}{\omega  \int _{\text{total}} \mu_0 \left|\vec{H}\right|^2 dV}
            \right]    = \dfrac{y_{\text{seam}} }{g_{\text{seam}}}
        See Brecht's thesis.
    
        :param g_seam: value for the g_seam. Indium gives more than 1e6.
        :param seam_line: string with the name of the seam line in HFSS.
        :param volume: string with the name of the volume in which the EM field lives in HFSS.
        :param coordinate_perp_to_line: The coordinate perpendicular to the seam line.
        """
        
        for mode_name, mode in (pbar := tqdm(self.format_dict.items())):
            pbar.set_description(f"Calculating seam loss for mode {mode_name}")
            self.eprh.set_mode(mode)
    
            omega = 2 * np.pi * self.freqs[mode] * 1e9
    
            calcobject = CalcObject([], self.eprh.setup)

            if coordinate_perp_to_line == 'x':
                j_surf = calcobject.getQty("Jsurf").scalar_x().smooth()
            elif coordinate_perp_to_line == 'y':
                j_surf = calcobject.getQty("Jsurf").scalar_y().smooth()
            elif coordinate_perp_to_line == 'z':
                j_surf = calcobject.getQty("Jsurf").scalar_z().smooth()
            else:
                raise ValueError(f'{coordinate_perp_to_line=}')

            # j_surf_conj = j_surf.conj()
            j_surf = j_surf.__mul__(j_surf.conj()).real()
            # j_surf = j_surf.real()
            int_j_surf = j_surf.integrate_line(name=seam_line)
            int_j_surf = int_j_surf.evaluate()
    
            vecH = calcobject.getQty("H").smooth()
            vecB = vecH.times_mu()
            squared_magnetic_field = vecH.dot(vecB.conj()).real()
            UH = squared_magnetic_field.integrate_vol(name=volume)
            UH = UH.evaluate()
    
            y_seam = int_j_surf / (UH * omega)
            print(f'y_seam = {y_seam:.2e} /(Ω*m)')
    
            Q_seam = g_seam / y_seam
            print(f'Q_seam = {Q_seam:.2e}')
            self.quality_factors[mode_name].seam_loss = Q_seam
        return

    def calculate_GF_factors(self, epsilon_r: float = 33, t_h: float = 5e-9, volume: str = 'AllObjects'):
        r"""
        Calculate the geometry (G-) and filling (F-) factors. Also calculates the mode volume in two ways.
        
        Here we use the equation
        .. math::
            G =\dfrac{\omega \mu_0}{\lambda p_\text{cond}} =
                \omega \mu_0 \dfrac{\int _{V} \left|{\vec{H}}\right|^2 dv}{\int _{S} \left|{\vec{H}}\right|^2 ds} \ ,
            \ F = \dfrac{\int _{V_h} \epsilon_h \left|{\vec{E}}\right|^2 dv}{\int _{V} \epsilon_0 \left|{\vec{E}}\right|^2 dv}
             \approx \dfrac{t_h \int _{S} \left|{\vec{E}}\right|^2 / (\epsilon_h/\epsilon_0) ds}{\int _{V}  \left|{\vec{E}}\right|^2 dv}

        Typical values $\epsilon_r = 33$ and $t_h = 5 \ nm$ dielectric thickness were used in
        https://journals.aps.org/prl/pdf/10.1103/PhysRevLett.119.264801, yielding F~3e-9, or even 1.2e-8 in
        https://link.aps.org/doi/10.1103/PhysRevApplied.13.034032.
        The nominator integral of the filling factor is divided by the relative permittivity since the electric field
            ($\vec{E}$) there is perpendicular to the vacuum-metal interface and hence smaller by that factor.
        See https://phys.libretexts.org/Bookshelves/Electricity_and_Magnetism/Book%3A_Electricity_and_Magnetism_(Tatum)/05%3A_Capacitors/5.14%3A__Mixed_Dielectrics.

        For the mode volume we use methods 2 and 3 from
            https://optics.ansys.com/hc/en-us/articles/360034395374-Calculating-the-modal-volume-of-a-cavity-mode.
        
        :param epsilon_r: relative permittivity of the dielectrics covering the surface.
        :param t_h: thickness of the dielectrics covering the surface.
        :param volume: string with the name of the volume in which the EM field lives in HFSS.
    
        :return factors: a list with the G and F factors of the modes, alternately. 
        """
    
        for mode_name, mode in (pbar := tqdm(self.format_dict.items())):
            pbar.set_description(f'Calculating G- and F-factors for {mode_name}')
            logger.info(f'{mode_name} results:')
            self.eprh.set_mode(mode)
    
            omega = 2 * np.pi * self.freqs[mode] * 1e9
    
            calcobject = CalcObject([], self.eprh.setup)
    
            # G Factor
            vecH = calcobject.getQty("H").smooth()
            vecB = vecH.times_mu()
            squared_magnetic_field = vecH.dot(vecB.conj()).real()
            UH_total = squared_magnetic_field.integrate_vol(name=volume).evaluate() * 0.5
    
            H_surface = vecH.dot(vecH.conj()).real().integrate_surf(name=volume)
            H_surface = H_surface.evaluate() * 0.5
            G = omega * (UH_total / H_surface)
            print(f'Geometry factor, G = {G:.2f} Ω')
            self.quality_factors[mode_name].G_factor_ohm = G
    
            # F Factor
            UE_total = get_electric_energy_in_volume(calcobject=calcobject, volume=volume)
            assert np.allclose(UE_total, UH_total, rtol=0.01)
            vecE = calcobject.getQty("E").smooth()
            vecD = vecE.times_eps()
            E_squared = vecE.dot(vecD.conj()).real()
            E_surface = E_squared.integrate_surf(name=volume).evaluate() / epsilon_r
            UE_surface = 0.5 * t_h * E_surface
            F = UE_surface / UE_total
            print(f'Filling factor, F = {F:.3}')
            self.quality_factors[mode_name].F_factor = F

            # mode volume - total energy divided by its maximum
            max_field = E_squared.maximum_vol(name=volume)
            max_energy_value = max_field.evaluate() / 2  # Convert to energy
            mode_volume = (UE_total / max_energy_value) * 1e6  # to cm^3
            print(f'Mode volume using max amplitude method = {mode_volume:.3} cm^3')
            self.quality_factors[mode_name].mode_volume_cm3_max_method = mode_volume

            # mode volume - (total magnetic energy)^2 divided total(magnetic energy squared)
            squared_magnetic_field = vecH.dot(vecB.conj()).real()
            total_squared_magnetic_field = squared_magnetic_field.integrate_vol(name=volume).evaluate()
            total_quadrupled_magnetic_field = (squared_magnetic_field * squared_magnetic_field).integrate_vol(
                name=volume).evaluate()
            mode_volume = ((total_squared_magnetic_field ** 2) / total_quadrupled_magnetic_field) * 1e6  # to cm^3
            print(f'Mode volume using magnetic field method = {mode_volume:.3} cm^3')
            self.quality_factors[mode_name].mode_volume_cm3_magnetic_field_method = mode_volume

        return
    
    def calculate_surface_losses(self, metal_surfaces, substrate,
                                 volume: str = 'AllObjects', epsilon_r: float = 10, t: float = 3e-9,
                                 loss_tangents=dict(tan_MA=2.1 * 1e-2, tan_MS=2.6 * 1e-3, tan_SA=2.2 * 1e-3)):
        r"""
        Calculate the surface losses.
        Here we calculate the surface participation ratios in order to estimate the losses due to them.
        The estimation is a very rough one, unlike the more complex, and probably more accurate, method used in
        http://aip.scitation.org/doi/10.1063/1.4934486 and http://arxiv.org/abs/2206.14334.
        The default values are also taken from the first paper.
    
        Similar to the calculation of the filling factor in the previous subsection we now calculate the participation
        ratio as
        $$    p_i = \dfrac{t \int_{S_i} \left| \vec{E} \cdot ( \vec{E}_\bot /\epsilon_r + \vec{E}_\parallel \times
        \epsilon_r) \right| ^{2} ds}{\int _{V} \left|\vec{E}\right| ^2 dv},$$
        where $i$ is the index of the interface over which the integral is done (MA, MS or SA).
        We use the values $\epsilon = 10 \epsilon_0$ and $t=3$ nm.
    
        The upper bound to the quality factor is then inversely-proportional to this participation ratio, i.e.
        $$ Q_i \leq \dfrac{1}{p_i \tan \delta_i}.$$
        For that we use upper bounds $\tan \delta_{MS} = 2.6 \times 10^{-3}, \ \tan \delta_{MA} = 2.1 \times 10^{-2}$
        and $\tan \delta_{SA} = 2.2 \times 10^{-3}$.

        :param epsilon_r: relative permittivity of the dielectrics covering the surface.
        :param t: thickness of the dielectrics covering the surfaces.
        :param volume: string with the name of the volume in which the EM field lives in HFSS.
        :param metal_surfaces: list of strings with the names of the metal surfaces on which the dielectrics reside.
        :param substrate: string with the name of the substrate (chip) on which the metal sheets are placed.
        :param loss_tangents: dictionary with the three relevant surface loss tangents, e.g.
            loss_tangents=dict(tan_MA=2.1 * 1e-2, tan_MS=2.6 * 1e-3, tan_SA=2.2 * 1e-3), which is an *upper bound*
            according to the reference mentioned above, Supplementary Material B.III.
    
        :return:
        """
    
        for mode_name, mode in (pbar := tqdm(self.format_dict.items())):
            pbar.set_description(f'Calculating surface losses for {mode_name}')
            print(f'Mode {mode_name} results:')
            self.eprh.set_mode(mode)
    
            calcobject = CalcObject([], self.eprh.setup)
    
            UE_total = get_electric_energy_in_volume(calcobject=calcobject, volume=volume)
            vecE = calcobject.getQty("E").smooth()
    
            # MA/MS participation ratio
            E_surface_metal = 0
            for metal_surface in metal_surfaces:
                # normal to surface
                vecE_normal = vecE.normal2surface(metal_surface)
                vecD_normal = vecE_normal.__mul__(epsilon_0 / epsilon_r)
                E_squared = (vecE_normal.dot(vecD_normal.conj())).real()
                E_surface_metal += E_squared.integrate_surf(name=metal_surface).evaluate() / 2

                # tangent to surface
                vecE_tangent = vecE.tangent2surface(metal_surface)
                vecD_tangent = vecE_tangent.__mul__(epsilon_r * epsilon_0)
                E_squared = (vecE_tangent.dot(vecD_tangent.conj())).real()
                E_surface_metal += E_squared.integrate_surf(name=metal_surface).evaluate() / 2

            p_metal = (t * E_surface_metal) / UE_total
            print(f'Metal-Air/Metal-Substrate participation ratio, p_MA = p_MS = {p_metal:.3}')
    
            # SA participation ratio
            vecE_normal = vecE.normal2surface(substrate).__mul__(epsilon_0 / epsilon_r)
            vecD_normal = vecE.normal2surface(substrate)
            vecE_tangent = vecE.tangent2surface(substrate)
            vecD_tangent = vecE.tangent2surface(substrate).__mul__(epsilon_0 * epsilon_r)
            E_squared = ((vecE_normal.dot(vecD_normal.conj())).__add__(
                (vecE_tangent.dot(vecD_tangent.conj())))).real()
            E_surface = E_squared.integrate_surf(name=substrate).evaluate() / 2
            E_surface_substrate = E_surface - E_surface_metal
    
            p_SA = (t * E_surface_substrate) / UE_total
            print(f'Air-Substrate participation ratio, p_SA = {p_SA:.3}')
    
            # upper bounds
            Q_MA = 1 / (p_metal * loss_tangents['tan_MA'])
            Q_MS = 1 / (p_metal * loss_tangents['tan_MS'])
            Q_SA = 1 / (p_SA * loss_tangents['tan_SA'])
            Q_surface_total = 1 / (1/Q_MA + 1/Q_MS + 1/Q_SA)
    
            print(f'Quality factor due to MA loss = {Q_MA:.3}')
            print(f'Quality factor due to MS loss = {Q_MS:.3}')
            print(f'Quality factor due to SA loss = {Q_SA:.3}')
            print(f'Quality factor due to all surface losses = {Q_surface_total:.3}')
    
            self.quality_factors[mode_name].surface_losses = Q_surface_total
    
    def calculate_bulk_loss(self, bulk: str, loss_tangent: float, volume: str = 'AllObjects'):
        r"""
        Calculate the bulk loss caused from a volume (usually the chip substrate).
        * Notice that the relative permittivity of the bulk should be defined in HFSS!

        See http://arxiv.org/abs/2206.14334. for details and a measured value for EFG sapphire loss tangent (62e-9).

        :param volume: string with the name of the volume in which the EM field lives in HFSS.
        :param bulk: string with the name of the bulk (usually the chip substrate) in which the losses occur.
        :param loss_tangent: the loss tangent of the bulk.
        """
    
        for mode_name, mode in (pbar := tqdm(self.format_dict.items())):
            pbar.set_description(f'Calculating bulk loss for {mode_name}')
            logger.info(f'{mode_name} results:')
            self.eprh.set_mode(mode)
    
            calcobject = CalcObject([], self.eprh.setup)
    
            total_UE = get_electric_energy_in_volume(calcobject=calcobject, volume=volume)
            bulk_UE = get_electric_energy_in_volume(calcobject=calcobject, volume=bulk)
            p_bulk = bulk_UE / total_UE
    
            bulk_Q_factor = 1 / (p_bulk * loss_tangent)
    
            print(f'Quality factor of mode {mode_name} due to bulk loss in {bulk} = {bulk_Q_factor:.2g}')
    
            self.quality_factors[mode_name].bulk_loss = bulk_Q_factor

    def calculate_coupling_losses(self, pin_surfaces: List[str], resistance: float = 50.0, volume: str = 'AllObjects'):
        r"""
        Doesn't work yet.
        """

        logger.warning("The method `calculate_coupling_losses` is not implemented!")
        # for mode_name, mode in (pbar := tqdm(self.format_dict.items())):
        #     pbar.set_description(f'Calculating coupling losses for {mode_name}')
        #     logger.info(f'{mode_name} results:')
        #     self.eprh.set_mode(mode)
        #     self.quality_factors[mode_name].coupling_losses = {}
        #
        #     omega = 2 * np.pi * self.freqs[mode] * 1e9
        #
        #     calcobject = CalcObject([], self.eprh.setup)
        #
        #     total_UE = get_electric_energy_in_volume(calcobject=calcobject, volume=volume) * epsilon_0
        #
        #     for pin_surface in pin_surfaces:
        #         I_peak = calcobject.getQty("Jsurf").tangent2surface(pin_surface).mag().integrate_surf(name=pin_surface)
        #         I_peak = I_peak.evaluate()
        #         dissipated_power = resistance * (I_peak / 2) ** 2
        #
        #         coupling_q_factor = omega * (total_UE / dissipated_power)
        #
        #         print(f'Quality factor of mode {mode_name} due to coupling loss in {pin_surface} = {coupling_q_factor:.2g}')
        #
        #         self.quality_factors[mode_name].coupling_losses[pin_surface] = coupling_q_factor

    def to_df(self, modes_to_remove: Optional[List[str]] = None) -> pd.DataFrame:
        if modes_to_remove is None:
            modes_to_remove = []
        quality_factors_df = pd.DataFrame.from_dict({k: v.to_dict() for k, v in self.quality_factors.items()
                                                     if k not in modes_to_remove})
        return quality_factors_df

    def to_csv(self, output_path: Optional[Union[str, Path]] = None, modes_to_remove: Optional[List[str]] = None):
        """Save the quality factors to a csv file."""
        now = f'_{datetime.now().strftime("%d_%m_%Y__%H_%M_%S")}'
        if output_path is None:
            output_path = Path(f'quality_factors_{self.name}_{now}')
        
        quality_factors_df = self.to_df(modes_to_remove=modes_to_remove)
        quality_factors_df.to_csv(Path(output_path).with_suffix('.csv'), float_format='%.2g')

    def to_markdown(self, modes_to_remove: Optional[List[str]] = None) -> str:
        """Return a markdown string with the quality factors."""
        quality_factors_df = self.to_df(modes_to_remove=modes_to_remove)
        return quality_factors_df.to_markdown(floatfmt='.2g')

    def to_latex(self, modes_to_remove: Optional[List[str]] = None) -> str:
        """Return a latex string with the quality factors."""
        quality_factors_df = self.to_df(modes_to_remove=modes_to_remove)
        return quality_factors_df.style.to_latex()
    
    def plot(self, modes_to_remove: Optional[List[str]] = None):
        """Plot the quality factors on a log scale."""
        quality_factors_df = self.to_df(modes_to_remove=modes_to_remove)
        quality_factors_df.plot(logy=True)
        plt.show()
