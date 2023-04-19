from dataclasses import dataclass, field
import pyEPR as epr


@dataclass
class Project:
    project_directory: str
    project_name: str  # file name
    design_name: str
    pinfo: epr.Project_Info = field(init=False)

    def __post_init__(self):
        self.pinfo = epr.Project_Info(project_path=self.project_directory,
                                      project_name=self.project_name,
                                      design_name=self.design_name)

    def get_project(self):
        return self.pinfo.project

    def get_setup(self, setup_name: str) -> epr.ansys.HfssSetup:
        return self.pinfo.design.get_setup(setup_name)

    def set_variable(self, name: str, value: str):
        if name.startswith('$'):
            self.pinfo.project.set_variable(name, value)
        else:
            self.pinfo.design.set_variable(name, value)

    def get_variable_value(self, name: str) -> str:
        return self.pinfo.project.get_variable_value(name)

    def delete_all_solutions(self):
        try:
            self.pinfo.design.delete_full_variation()
        except Exception as e:
            print('No solutions found')