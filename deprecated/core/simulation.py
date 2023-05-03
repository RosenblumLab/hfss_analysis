from dataclasses import dataclass
import pyEPR as epr


@dataclass
class Simulation:
    project: Project
    setup_name: str
    format_dict: Dict[str, int] = None
    junctions: Dict[str, Dict[str, str]] = None
    eigenmodes: pd.DataFrame = field(default_factory=pd.DataFrame)
    chi_matrix: pd.DataFrame = field(default_factory=pd.DataFrame)
    ND_freqs: pd.DataFrame = field(default_factory=pd.DataFrame)  # Frequencies from numerical diagonalization

    def __post_init__(self):
        # check the validity of the format dict
        if self.format_dict is None:
            self.format_dict = {f'Mode {i}': i for i in range(3)}

    def clear(self):
        self.eigenmodes = pd.DataFrame()
        self.chi_matrix = pd.DataFrame()
        self.ND_freqs = pd.DataFrame()

    def analyze_classic(self):
        # analysing
        setup = self.project.get_setup(self.setup_name)
        if setup.basis_order != str(epr.ansys.BASIS_ORDER['Mixed Order']):
            epr.logger.warning('Setup order is not set to "Mixed Order", which usually gives the best results.')

        setup.analyze()

    def get_variations_dict(self):
        return epr.DistributedAnalysis(self.project.pinfo).get_variations()

    def extract_all_eigenmodes(self, variation_iter: Optional[Iterable[str]] = None):
        eprh = epr.DistributedAnalysis(self.project.pinfo)
        variation_iter = eprh.variations if variation_iter is None else variation_iter
        for variation_num in variation_iter:
            # getting frequencies
            df = eprh.get_freqs_bare_pd(variation_num)

            # formatting them
            if self.format_dict is not None:
                df = parse_eigenmodes_results(df, self.format_dict)

            # adding them to the results
            self.eigenmodes = pd.concat([self.eigenmodes, df], ignore_index=True)

    def make_classic(self) -> pd.DataFrame:
        # analysing
        self.analyze_classic()

        # saving results
        self.extract_all_eigenmodes()

        return self.eigenmodes

    def add_junctions(self):
        for junction_name, value in self.junctions.items():
            self.project.pinfo.junctions[junction_name] = value
        self.project.pinfo.validate_junction_info()

    def make_quantum(self, variations_iter: Optional[Iterable[str]] = None):
        # first check the validity of the format dict
        if self.format_dict is None:
            raise ValueError('For quantum simulation format_dict is needed!')

        modes = list(self.format_dict.values())

        if len(modes) > 3:
            raise ValueError(f'Support only up to 3 modes for quantum simulation!! Given: {self.format_dict}')

        if self.junctions is None:
            raise ValueError(f'Please supply junctions for quantum analysis')

        # adding junctions
        self.add_junctions()

        # make analysis and get chi matrix
        chi_matrix, ND_freqs = do_quantum_analysis(self.project.pinfo, modes)

        # formatting chi matrix and ND frequencies to fit format dict
        chi_matrix = format_all_chis(chi_matrix, self.format_dict, variations_iter=variations_iter)
        ND_freqs = format_ND_freqs(ND_freqs, self.format_dict, variations_iter=variations_iter)

        # adding them to the results
        self.chi_matrix = pd.concat([self.chi_matrix, chi_matrix])
        self.ND_freqs = pd.concat([self.ND_freqs, ND_freqs])

    def concat_eigenmodes_chi_and_ND_freqs(self):
        # parsing eigenmodes according to the format dict
        return pd.concat([self.ND_freqs, self.chi_matrix, self.eigenmodes], axis=1)

    def make_all(self):
        self.make_classic()
        self.make_quantum()
        return self.concat_eigenmodes_chi_and_ND_freqs()