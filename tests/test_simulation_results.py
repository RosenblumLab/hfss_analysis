from hfss_analysis.simulation_basics.simulation_result import join, SimulationResult
from hfss_analysis.variables.variables import ValuedVariable


v_a = ValuedVariable('$LLLL', 11.015, 'mm')
v_b = ValuedVariable('hiho', 8, '')
v_c = ValuedVariable('bye', 1, '')


data = [
    SimulationResult(result={'name': 'hi'}, snapshot=(v_a, v_b)),
    SimulationResult(result={'is_horse': True}, snapshot=(v_a, v_b)),
    SimulationResult(result={'is_not_horse': False}, snapshot=(v_a, v_b)),
    SimulationResult(result={'who_am_i': 'hi'}, snapshot=(v_a, v_c)),
    SimulationResult(result={'i_know_who_i_am': True}, snapshot=(v_a, v_c)),
]

expected = [
    SimulationResult(result={'name': 'hi', 'is_horse': True,
                             'is_not_horse': False}, snapshot=(v_a, v_b)),
    SimulationResult(result={'who_am_i': 'hi',
                             'i_know_who_i_am': True}, snapshot=(v_a, v_c)),
]

def test_simulation_results_merge():
    result = join(data)
    assert(result == expected)