import numpy as np
import pandas as pd
import pyEPR as epr
from pyEPR.core import *
from pyEPR import calcs
from pyEPR.core_distributed_analysis import *

mu_0 = 4 * np.pi * 1e-7

class HFSSproject:

    def __init__(self, project_name, project_path='.'):
        self.project_path = project_path
        self.project_name = project_name
        self.quality_factors = {}

    

    def HFSS_analyze(self, design_name):
        pinfo = epr.Project_Info(project_path = self.project_path,
                        project_name = self.project_name,  # File name
                         design_name  = design_name)
        pinfo.setup.analyze()
        eprh = epr.DistributedAnalysis(pinfo)
        return eprh

    def get_quality_factor(self, design_name, modes=[0], quality_factor_name = None, print_results = False):
        '''
        This function runs a simple simulation of an HFSS design when no calculations are needed.

        :param modes: a list of mode numbers whose Q-factors need to be calculated.
        :param quality_factor_name: key name for dictionary. If None the function uses the design name.
        :param display_results: whether to display the results or not.
        '''

        if quality_factor_name == None:
            quality_factor_name = design_name

        eprh = self.HFSS_analyze(design_name)
        df = eprh.get_freqs_bare_pd(eprh.variations[0])

        for mode in modes:
            if f'mode {mode}' not in self.quality_factors:
                self.quality_factors[f'mode {mode}'] = {}
            self.quality_factors[f'mode {mode}'][quality_factor_name] = df['Quality Factor'][mode]
        
        if print_results:
            df['Lifetime (s)'] = df['Quality Factor']/(2*np.pi*df['Freq. (GHz)']*1e9)
            print(df)

        return

    def calculate_seam_loss(self, design_name, g_seam, seam_line, volume, modes=[0]):
        '''
        Here we use the equation $$\dfrac{1}{Q_{\text{seam}}} = \dfrac{L}{G_{\text{seam}}} \left[ 
        \dfrac{\int _{\text{seam}} \left| \vec{J}_s \times \hat{l}\right|^{2}dl}{\omega  \int _{\text{total}} \mu_0 \left|\vec{H}\right|^2 dV}
        \right]    = \dfrac{y_{\text{seam}} }{g_{\text{seam}}}$$.

        :param modes: a list of mode numbers whose seam Q-factors need to be calculated.
        :param g_seam: value for the g_seam. Indium gives 1e6.
        :param seam_line: string with the name of the seam line in HFSS.
        :param volume: string with the name of the volume in which the EM field lives in HFSS.

        :return Q_seam: 
        '''
          
        eprh_seam = self.HFSS_analyze(design_name)
        F_seam, Qs = eprh_seam.get_freqs_bare_pd(variation='0').values.transpose()

        for mode in modes:
            if f'mode {mode}' not in self.quality_factors:
                self.quality_factors[f'mode {mode}'] = {}
            print(f'\nMode {mode} results:')
            eprh_seam .set_mode(mode)

            omega = 2*np.pi*F_seam[mode]*1e9

            calcobject = CalcObject([], eprh_seam .setup)

            j_surf = calcobject.getQty("Jsurf").scalar_z().smooth()
            j_surf_conj = j_surf.conj()
            j_surf = j_surf.__mul__(j_surf_conj)
            j_surf = j_surf.real()
            int_j_surf = j_surf.integrate_line(name=seam_line)
            int_j_surf = int_j_surf.evaluate()

            vecH = calcobject.getQty("H").smooth()
            A = vecH
            #A = A.times_mu()
            B = vecH.conj()
            A = A.dot(B)
            A = A.real()
            UH = A.integrate_vol(name=volume)
            UH = UH.evaluate()
            UH = UH*mu_0

            y_seam = int_j_surf/UH/omega
            print(f'y_seam = {y_seam:.2e} /(Ω*m)')

            Q_seam = g_seam/y_seam
            tau_seam = Q_seam/omega
            print(f'Q_seam = {Q_seam:.2e}')
            print(f'tau_seam = {tau_seam:.2e} s')
            self.quality_factors[f'mode {mode}']['seam_loss'] = Q_seam
        return


    def calculate_GF_factors(self, design_name, epsilon_r, t_h, volume, modes=[0]):
        '''
        Calculate the geormetry (G-) and filling (F-) factors.
        Here we use the equation 
        $$ G =\dfrac{\omega \mu_0}{\lambda p_\text{cond}} =  \omega \mu_0 \dfrac{\int _{V} \left|{\vec{H}}\right|^2 dv}{\int _{S} \left|{\vec{H}}\right|^2 ds} \ ,
         \ F= \dfrac{\int _{V_h} \epsilon_h \left|{\vec{E}}\right|^2 dv}{\int _{V} \epsilon_0 \left|{\vec{E}}\right|^2 dv} 
         \approx \dfrac{t_h \int _{S}  \left|{\vec{E}}\right|^2 / (\epsilon_h/\epsilon_0) ds}{\int _{V}  \left|{\vec{E}}\right|^2 dv},$$
        with the values $\epsilon_h = 33 \epsilon_0$ (https://journals.aps.org/prl/pdf/10.1103/PhysRevLett.119.264801) 
        and $t_h = 5 \ nm$ dielectric thickness. The nominator integral of the filling factor is divided by the relative premittivity since the electric field ($\vec{E}$) 
        there is perpendicular to the vacuum-metal interface and hence smaller by that factor. 
        See https://phys.libretexts.org/Bookshelves/Electricity_and_Magnetism/Book%3A_Electricity_and_Magnetism_(Tatum)/05%3A_Capacitors/5.14%3A__Mixed_Dielectrics.

        :param modes: a list of mode numbers whose G- and F-factors need to be calculated.
        :param epsilon_r: realtive permittivity of the dielectrics covering the surface.
        :param t_h: thickness of the dielectrics covering the surface.
        :param volume: string with the name of the volume in which the EM field lives in HFSS.

        :return factors: a list with the G and F factors of the modes, alternately. 
        '''

        eprh_GF_factors = self.HFSS_analyze(design_name)
        Freq, Q = eprh_GF_factors.get_freqs_bare_pd(variation='0').values.transpose()

        for mode in modes:
            if f'mode {mode}' not in self.quality_factors:
                self.quality_factors[f'mode {mode}'] = {}
            print(f'\nMode {mode} results:')
            eprh_GF_factors.set_mode(mode)

            omega = 2*np.pi*Freq[mode]*1e9

            calcobject = CalcObject([], eprh_GF_factors.setup)

            #G Factor
            vecH = calcobject.getQty("H").smooth()
            A = vecH
            B = vecH.conj()
            A = A.dot(B)
            A = A.real()
            UH = A.integrate_vol(name=volume)
            UH = UH.evaluate()
            UH = UH*mu_0*omega

            H_surface = A.integrate_surf(name=volume)
            H_surface = H_surface.evaluate()
            G = UH/H_surface
            print(f'Geometry factor, G = {G:.2f} Ω')
            self.quality_factors[f'mode {mode}']['geometry_factor'] = G

            #F Factor
            vecE = calcobject.getQty("E").smooth()
            A = vecE
            B = vecE.conj()
            A = A.dot(B)
            A = A.real()
            UE = A.integrate_vol(name=volume)
            UE = UE.evaluate()

            E_surface = A.integrate_surf(name=volume)
            E_surface = E_surface.evaluate()
            F = (t_h * E_surface) / (epsilon_r*UE)
            print(f'Filling factor, F = {F:.3}')
            self.quality_factors[f'mode {mode}']['filling_factor'] = F

        return