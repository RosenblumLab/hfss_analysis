from hfss_analysis import classical_analysis

modes_to_labels = {
    0: 'transmon',
    1: 'cavity',
    3: 'readout'
}

data = [{'Freq. (GHz)': {0: 4.08113193501,
                         1: 4.44545927843,
                         2: 7.28449464161,
                         3: 7.86158266318,
                         4: 9.04097662663},
         'Quality Factor': {0: 1153385.2624367443,
                            1: 82491407.09043404,
                            2: 2.1564913964190415,
                            3: 2057.667998776121,
                            4: 2.3151551887708735},
         'Lifetime (us)': {0: 44.979424514905084,
                           1: 2953.331563456618,
                           2: 4.7116002188365626e-05,
                           3: 0.04165675631460691,
                           4: 4.075537494836774e-05}},
        {'Freq. (GHz)': {0: 4.06849811727,
                         1: 4.44383800301,
                         2: 7.28137953071,
                         3: 7.86118517231,
                         4: 9.03254234675},
         'Quality Factor': {0: 1203488.033895741,
                            1: 79440515.81496766,
                            2: 2.158539718459011,
                            3: 2090.8856391390186,
                            4: 2.3168410487041045},
         'Lifetime (us)': {0: 47.0790606325706,
                           1: 2845.142141805825,
                           2: 4.718093111394802e-05,
                           3: 0.04233137594582907,
                           4: 4.0823136067792035e-05}},
        {'Freq. (GHz)': {0: 4.12612839489,
                         1: 4.4408953982,
                         2: 7.27389763816,
                         3: 7.84162736092,
                         4: 9.02663900905},
         'Quality Factor': {0: 1177029.850698635,
                            1: 79523150.5962531,
                            2: 2.1579796097306465,
                            3: 2219.933539081613,
                            4: 2.316630089521901},
         'Lifetime (us)': {0: 45.40094271845784,
                           1: 2849.988881243378,
                           2: 4.7217205831759716e-05,
                           3: 0.04505613182298328,
                           4: 4.084611445003763e-05}},
        {'Freq. (GHz)': {0: 4.08487657828,
                         1: 4.44655287182,
                         2: 7.2780154913,
                         3: 7.85785827042,
                         4: 9.03399651165},
         'Quality Factor': {0: 1217022.8541253638,
                            1: 77995713.15204579,
                            2: 2.157474957488015,
                            3: 2157.5748948539,
                            4: 2.3162028001451103},
         'Lifetime (us)': {0: 47.417639034620876,
                           1: 2791.6913721628057,
                           2: 4.717945496154215e-05,
                           3: 0.04370003858425668,
                           4: 4.0805320698430824e-05}}]


expected = [{'cavity Freq. (GHz)': 4.44545927843,
             'cavity Lifetime (us)': 2953.331563456618,
             'cavity Quality Factor': 82491407.09043404,
             'readout Freq. (GHz)': 7.86158266318,
             'readout Lifetime (us)': 0.04165675631460691,
             'readout Quality Factor': 2057.667998776121,
             'transmon Freq. (GHz)': 4.08113193501,
             'transmon Lifetime (us)': 44.979424514905084,
             'transmon Quality Factor': 1153385.2624367443},
            {'cavity Freq. (GHz)': 4.44383800301,
             'cavity Lifetime (us)': 2845.142141805825,
             'cavity Quality Factor': 79440515.81496766,
             'readout Freq. (GHz)': 7.86118517231,
             'readout Lifetime (us)': 0.04233137594582907,
             'readout Quality Factor': 2090.8856391390186,
             'transmon Freq. (GHz)': 4.06849811727,
             'transmon Lifetime (us)': 47.0790606325706,
             'transmon Quality Factor': 1203488.033895741},
            {'cavity Freq. (GHz)': 4.4408953982,
             'cavity Lifetime (us)': 2849.988881243378,
             'cavity Quality Factor': 79523150.5962531,
             'readout Freq. (GHz)': 7.84162736092,
             'readout Lifetime (us)': 0.04505613182298328,
             'readout Quality Factor': 2219.933539081613,
             'transmon Freq. (GHz)': 4.12612839489,
             'transmon Lifetime (us)': 45.40094271845784,
             'transmon Quality Factor': 1177029.850698635},
            {'cavity Freq. (GHz)': 4.44655287182,
             'cavity Lifetime (us)': 2791.6913721628057,
             'cavity Quality Factor': 77995713.15204579,
             'readout Freq. (GHz)': 7.85785827042,
             'readout Lifetime (us)': 0.04370003858425668,
             'readout Quality Factor': 2157.5748948539,
             'transmon Freq. (GHz)': 4.08487657828,
             'transmon Lifetime (us)': 47.417639034620876,
             'transmon Quality Factor': 1217022.8541253638}]


def test_classical_formatter():
    result = classical_analysis.apply_format_dict(data, modes_to_labels=modes_to_labels)
    assert result == expected


