from hfss_analysis.hfss_project.project import Project
import pandas as pd


def classical_analysis(project: Project) -> pd.DataFrame:
    # get current snapshot of parameters
    snapshot = project.get_all_variables()

    # hfss analysing
    project.analyze()

    # get results
    return project.get_analysis_results(snapshot)

