import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import pyEPR as epr
from itertools import product
from tqdm import tqdm


def multi_parameter_sweep(pinfo, analyzed_modes, swept_variables, variations_lists, units=None, filename=None):
    """
    Run many HFSS+pyEPR simulations with varying parameter(s). The results, including mode frequencies, lifetimes and
    non-linear properties, are returned as a pandas DataFrame and optionally saved as a csv file.
    A use example is given in the end of this file.

    :param pinfo: pyEPR ProjectInfo object with Josephson junctions.
    :param analyzed_modes: list of the mode numbers to be analyzed in HFSS.
    :param swept_variables: list of variables to be swept.
    :param variations_lists: list of lists with the values the swept variable will take. The number of lists must agree
    with the number of swept variables. For example:
    variations_lists = [np.linspace(variations_starts[i], variations_ends[i], variations_nums[i])
    for i in range(len(swept_variables))]
    :param units: list of strings with the units corresponding to the values in the variations list. Default to um.
    :param filename: string. If given and not None the results DataFrame is saved under this name.
    :return results_df: results DataFrame with the following columns - variables, freqs, lifetimes, alphas, couplings
    """

    if len(swept_variables) != len(variations_lists):
        raise ValueError (f'The number of variations lists (={len(variations_lists)}) must agree with the number of'
                          f'swept variables (={len(swept_variables)})')
    pinfo.validate_junction_info()

    try:
        pinfo.design.delete_full_variation()  # Delete existing solutions
        pinfo.design.Clear_Field_Clac_Stack()  # Clear calculator stack
        epr.logger.info('Previous solutions cleaned-up!')
    except:
        epr.logger.info('No previous solutions to be deleted!')

    variation_tuples_list = list(product(*variations_lists))

    variables_df = pd.DataFrame(index=[str(i) for i in range(len(variation_tuples_list))], columns=swept_variables)
    variables_df.index.name = 'variation'

    units = units or ['um']*len(swept_variables)
    for n_variation, variation_tuple in enumerate(tqdm(variation_tuples_list)):
        for j, variable in enumerate(swept_variables):
            swp_val = f'{variation_tuple[j]}{units[j]}'
            # epr.logger.info(f'Setting sweep variable {variable}={swp_val}')
            pinfo.design.set_variable(variable, swp_val)
            variables_df[variable][n_variation] = variation_tuple[j]

        # HFSS analysis
        pinfo.setup.analyze()

    # Classical calculations
    eprh = epr.DistributedAnalysis(pinfo)
    eprh.do_EPR_analysis(modes=analyzed_modes)

    # Quantum calculations (numerical diagonalization)
    epra = epr.QuantumAnalysis(eprh.data_filename)
    print('Starting numerical diagonalizations.')
    epra.analyze_all_variations(cos_trunc=8, fock_trunc=15)
    print('Finished numerical diagonalizations.')

    # Frequencies (from numerical diagonalization)
    freqs_df = epra.get_frequencies(numeric=True).transpose()
    freqs_df.columns.name = None
    freqs_df.columns = [f'Freq ND {mode} [MHz]' for mode in freqs_df.columns]

    # Quality Factors (from classical simulation)
    Qs_df = epra.get_quality_factors().transpose()
    Qs_df.columns = [f'Q {mode}' for mode in Qs_df.columns]
    Qs_df.index = variables_df.index

    chis = epra.get_chis()
    idx = pd.IndexSlice

    # Anharmonicities
    alphas_df = pd.DataFrame()
    for mode in analyzed_modes:  # mode index number, mode index
        alphas_df[f"Anharmonicity {mode} [MHz]"] = chis.loc[idx[:, mode], mode].unstack(1)
        # alpha.index = variations_vector

    # Cross-Kerr
    couplings_df = pd.DataFrame()
    for mode in analyzed_modes:
        for mode2 in analyzed_modes:
            if int(mode2) > int(mode):
                couplings_df[f"Cross-Kerr {mode}-{mode2} [MHz]"] = chis.loc[idx[:, mode], mode2].unstack(1)

    results_df = pd.concat([variables_df, freqs_df, Qs_df, alphas_df, couplings_df], axis=1)

    # Turn Quality factor into lifetime
    for mode in analyzed_modes:
        results_df[f'Q {mode}'] = results_df[f'Q {mode}'] / (2 * np.pi * results_df[f'Freq ND {mode} [MHz]'])
        results_df.rename(columns={f'Q {mode}': f'lifetime {mode} [us]'}, inplace=True)

    if filename is not None:
        results_df.to_csv(f'{filename}.csv')
        print(f'{filename}.csv saved!')

    return results_df

if __name__ == '__main__':

    analyzed_modes = [0, 1, 2]

    filename = 'results_df_8nH'
    TransmonPadWidth = 304.5
    filename += f'_BrightTransmonXshift945_TransmonPadWidth{TransmonPadWidth}'

    # Prepare a list of variation tuples
    swept_variables = ['TransmonPadLength',
                       'TransmonsDistance', 'DarkTransmonPadLength', 'DarkTransmonPadWidth']
    variations_starts = [0.95 * 590, 0.95 * 150, 0.95 * 560, 0.95 * 560]
    variations_ends = [1.05 * 590, 1.05 * 150, 1.05 * 560, 1.05 * 560]
    variations_nums = [3, 3, 3, 3]
    variations_lists = [np.linspace(variations_starts[i], variations_ends[i], variations_nums[i])
                        for i in range(len(swept_variables))]

    pinfo = epr.Project_Info(project_path='.',
                             project_name='QuantumZeno',  # File name
                             design_name='WithPins')

    pinfo.junctions['j1'] = {'Lj_variable': 'BrightTransmonLj',
                             'rect': 'BrightTransmonJJ',
                             'line': 'BrightJJline'}

    pinfo.junctions['j2'] = {'Lj_variable': 'DarkTransmonLj',
                             'rect': 'DarkTransmonJJ',
                             'line': 'DarkJJline'}
    pinfo.validate_junction_info()

    df = multi_parameter_sweep(pinfo=pinfo, analyzed_modes=analyzed_modes, swept_variables=swept_variables,
                     variations_lists=variations_lists, units=None, filename=filename)
