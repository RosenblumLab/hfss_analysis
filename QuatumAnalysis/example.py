from qunatum_analysis import Project, Sweep, Variable, Simulation



project = Project(
    project_directory=r'D:\Users\physicsuser\Desktop\Model\.',
    project_name='correct_cavity_model',  # File name
    design_name='HFSSDesign1'
)

# original 10.8
resonator_length_var = Variable(
    design_name='$ReadoutResonator_legnth',
    display_name='Readout length',
    units='mm',
    iterable=[10.6, 10.7]
)


# original 9.9
transmon_pin_length_var = Variable(
    design_name='$TransmonDrivePin_length',
    display_name='Transmon drive pin length',
    units='mm',
    iterable=[9.5, 9.6, 9.7, 9.8]
)


# original 31.05
chip_z_position = Variable(
    design_name='$ChipBase_z',
    display_name='Chip Penetration',
    units='mm',
    iterable=[31.05, 31.25, 31.45, 31.65]
)


format_dict = {
    'Cavity': 0,
    'Transmon': 1,
    'Readout': 3
}

junctions_dict = {
    'j1': {'Lj_variable': 'Lj',
           'rect': 'JJ',
           'line': 'line_jj1'}
}


simulation = Simulation(
    project=project,
    setup_name='Setup1',
    format_dict=format_dict,
    junctions=junctions_dict
)

sweep = Sweep(
    simulation=simulation,
    variables=[resonator_length_var, transmon_pin_length_var, chip_z_position]
)


project.delete_all_solutions()
setup = project.get_setup('Setup1')
setup.passes = 4
result = sweep.make_all()
result.to_csv('sweep.csv')


