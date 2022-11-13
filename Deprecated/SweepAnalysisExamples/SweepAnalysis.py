import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import pyEPR as epr
import pickle


def save_simulation(simulation, file_name: str = 'last_simulation'):
    simulation.pinfo = None
    simulation.eprh = None
    with open(file_name + '.pickle', 'wb') as handle:
        pickle.dump(simulation, handle)


def load_simulation(file_name: str = 'last_simulation'):
    with open(file_name + '.pickle', 'rb') as handle:
        simulation = pickle.load(handle)

    return simulation


class SweepAnalysis:

    def __init__(self, project_info, var_name):
        self.pinfo = project_info
        self.var_name = var_name
        self.n_modes = int(self.pinfo.setup.n_modes)

        # sweep parameters
        self.start_val = None
        self.stop_val = None
        self.step_val = None
        self.sweep_array = None

        # simulation result
        self.eprh = None
        self.freqs = None
        self.Q_factors = None
        self.taus = None

    def get_current_value(self):
        current_value = self.pinfo.design.get_variable_value(self.var_name)
        print(self.var_name + ' = ' + current_value)
        return current_value

    def sweep(self, start, stop, step):
        self.start_val = step
        self.stop_val = stop
        self.step_val = step

        self.sweep_array = np.arange(start, stop + step, step)

        for swp_param in self.sweep_array:
            swp_val = self.to_swp_val(swp_param)
            epr.logger.info(f'Setting sweep variable {self.var_name}={swp_val}')
            self.pinfo.design.set_variable(self.var_name, swp_val)
            self.pinfo.setup.analyze()

        self.eprh = epr.DistributedAnalysis(self.pinfo)

    def get_results(self, modes):
        if self.eprh is None:
            raise Exception('Simulation was not performed.')

        modes = self.validate_modes(modes)

        self.freqs = np.zeros((len(modes), len(self.sweep_array)))
        self.Q_factors = np.zeros_like(self.freqs)
        self.taus = np.zeros_like(self.freqs)

        for j, var in enumerate(range(len(self.sweep_array))):
            try:
                print('Variation number {}: \n '.format(var),
                      self.eprh.get_freqs_bare_pd(variation=str(var)))

                for mode in modes:
                    self.Q_factors[mode, j] = self.eprh.get_freqs_bare_pd(variation=str(var)).iloc[mode]['Quality Factor']
                    self.freqs[mode, j] = self.eprh.get_freqs_bare_pd(variation=str(var)).iloc[mode]['Freq. (GHz)']
                    self.taus[mode, j] = self.Q_factors[mode, j] / (2 * np.pi * np.array(self.freqs[mode, j]) * 1e9)

            except Exception as e:
                print('Error in variation', var, e)
                self.sweep_array = np.delete(self.sweep_array, var)
                continue

    def show_freqs(self, modes):
        """
        Plot the mode frequency as a function of the sweep parameter for the modes specified by modes.
        :param modes: list of modes.
        """
        modes = self.validate_modes(modes)

        fig, ax = plt.subplots()
        for mode in modes:
            ax.plot(self.sweep_array, self.freqs[mode, :], label='mode {}'.format(mode))

        ax.set(xlabel=self.var_name, ylabel='frequency [GHz]')
        ax.set_yscale('log')
        ax.legend()
        plt.show()

    def show_Q_factors(self, modes):
        """
        Plot the Q factor as a function of the sweep parameter for the modes specified by modes.
        :param modes: list of modes.
        """
        modes = self.validate_modes(modes)

        fig, ax = plt.subplots()
        for mode in modes:
            ax.plot(self.sweep_array, self.Q_factors[mode, :], label='mode {}'.format(mode))

        ax.set(xlabel=self.var_name, ylabel='Q factor')
        ax.set_yscale('log')
        ax.legend()
        plt.show()

    def validate_modes(self, modes):
        """
        A method to validate the modes input.
        :param modes: A list of the modes which should be analyzed / plotted.
        :return: Returns a list of length min(len(modes), n_modes) with the modes to analyze/plot.
        """

        if not isinstance(modes, list):
            modes = [modes]
        if len(modes) > self.n_modes:
            print('Analysis setup has only {} modes. Reducing modes list.'.format(self.n_modes))
            modes = np.arange(0, self.n_modes).tolist()

        return modes

    @staticmethod
    def to_swp_val(x):
        return f'{x}mm'


if __name__ == '__main__':
    project_path = r'C:/Users/rosengrp/Documents/3D Designs/Double cavity/double_cavity_hfss'
    project_name = r'DoubleCavity'
    design_name = r'DoubleCavity'
    pinfo = epr.Project_Info(project_path=project_path,
                                    project_name=project_name,
                                    design_name=design_name)

    sim = SweepAnalysis(project_info=pinfo, var_name='pin3_length')
    sim.sweep(start=3, stop=6.5, step=0.1)
    sim.get_results(modes=[0, 1])
    save_simulation(sim, file_name='short_simulation')

    sim.show_freqs(modes=[0, 1])
    sim.show_Q_factors(modes=[0, 1])

    # sim = load_simulation(file_name='short_simulation')


