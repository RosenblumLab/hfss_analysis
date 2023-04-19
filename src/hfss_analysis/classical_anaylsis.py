from .core.project import Project
import pyEPR as epr


def run_setup(project: Project, setup_name: str):
    # analysing
    setup = project.get_setup(setup_name)
    if setup.basis_order != '-1':
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


def analyze(project: Project, setup_name: str) -> pd.DataFrame:
    # analysing
    run_setup(project, setup_name)

    # extracting the results and returning them
    self.extract_all_eigenmodes()

    return self.eigenmodes