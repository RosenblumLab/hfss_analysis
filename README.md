# HFSS analysis package

## Introduction
This package facilitates the usage of HFSS simulation with [pyEPR](https://github.com/zlatko-minev/pyEPR) quantum analysis package. 
The goals of this package are as follows:
1. easy to execute classical and quantum simulations (as well as other analysis modules: losses etc...)
2. support sweep over range of parameters with different strategies (product, zip, ...)
3. export all data to a csv with all dynamic parameters appended  

## Installation
```commandline
git clone <this repo>
git clone <pyEPR-quantum repo>

pip install -e <this repo local path>
pip install -e <pyEPR-quantum repo local path>
```

## Usage
```python
from hfss_analysis import classical_analysis, quantum_analysis, Sweep, \
    join, minimize_results, Project, Variable


# instantiation of the project class, pointing to existing HFSS design and setup.
project = Project(
    project_directory=r'PATH_TO_PROJECT_DIR',
    project_name='PROJECT_NAME',  # File name
    design_name='DESIGN_NAME',
    setup_name='SETUP_NAME'
)

# adding Josephson junctions if we want to do quantum analysis
junctions_dict = {
    'j1': {'Lj_variable': 'Lj',
           'rect': 'JJ',
           'line': 'line_jj1'}
}

project.add_junctions(junctions_dict)


# Some variables that we want to scan over their iterable values
#   in this case we are adding only one variable, meaning at each iteration
#   the sweep will change $ChipBase_z value to one that is given in the iterable
chip_z_position = Variable(
    name='$ChipBase_z',
    units='mm',
    iterable=[31.05, 31.25, 31.45, 31.65]
)


# The `variables` argument can be a list of many `Variable` instances.
#   based on the given strategy the `Sweep` class convert a list of Variable
#   to a list of `ValuedVariable` which is a class same as `Variable` but contain only 
#   one value (not iterable).
sweep = Sweep(
    project=project,
    variables=[chip_z_position]
)


# Used for formatting the mode number into a meaningful name. Otherwise, the mode numbers will be used.
modes_to_labels = {
    0: 'transmon',
    1: 'cavity',
    3: 'readout'
}


# making simulation
raw_classical_results = classical_analysis.analyze(project, sweep)
raw_quantum_results = quantum_analysis.analyze(project, list(modes_to_labels.keys()), sweep)

# formatting the result and flatten it
formatted_classical_results = classical_analysis.apply_format(raw_classical_results, modes_to_labels)
formatted_quantum_results = quantum_analysis.apply_format(raw_quantum_results, modes_to_labels)

# joining the classical and quantum result to a single result
joint_results = join(formatted_classical_results + formatted_quantum_results)

# minimizing - given a list of simulation result this function finds the minimal set of changes
#               between the different iterations (in our case it is only the '$ChipBase_z' parameter)
#               and return a snapshot of all the constant variables (everything beside $ChipBase_z)
#               and a list of simulation results with the minimized snapshot
results = minimize_results(joint_results)

# saving
results.save_to_csv('sample.csv')
```

## Key concepts
In the example above I used some classes and function which i'll explain their goal in the following:
### `Variable` & `ValuedVariable`
Represent a variable in HFSS. Its name must be equal to either a design name or project name of variable.
Using its `.gen` method it generates ValuedVariable object, which is the same as Variable but support 
only one value (float) and not iterable. Generally Variable is used for sweep while ValuedVariable is used 
for snapshots.


### snapshot
A tuple of `ValuedVariable` instances. This is used as the ID of a given simulation. As the HFSS has memory and when
doing classical simulation we can do many changes and after each change to run analyze the HFSS saves all the results in
its memory. When one want to access one of the results it is usually done using a 'variation_number'. However sometimes
these variation numbers are not consistent hence we find it is better to save all the parameters used in the given
simulation and use it as an ID for the simulation result. In addition, given a set of simulation results and their
snapshots we can minimize the snapshots such that it will find all the variables that are different between the results
and all the variables that are constant (used for saving the results to csv - showing only the variables that are
different).

### sweep
in charge of generating the desired sequence for parameter sweeping and setting the design accordingly.
In order to construct a sequence of parameters it uses a strategy.
Currently, supported strategies are: product and zip.
- **product**: all combinations of list of iterables. e.g.: `[[1,2], [3,4]] -> [(1,3), (1,4), (2, 3), (2, 4)]`
- **zip**: one element from each iterable: e.g.: `[[1,2], [3,4]] -> [(1,3), (2,4)]`

