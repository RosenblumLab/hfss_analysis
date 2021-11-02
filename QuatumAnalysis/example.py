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


# original 10.2
transmon_pin_length_var = Variable(
    design_name='$TransmonDrivePin_length',
    display_name='Transmon drive pin length',
    units='mm',
    iterable=[10, 10.1, 10.2]
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
    variables=[resonator_length_var]
)


project.delete_all_solutions()
setup = project.get_setup('Setup1')
setup.passes = 4
result = sweep.make_all()
result.to_csv('sweep4.csv')


