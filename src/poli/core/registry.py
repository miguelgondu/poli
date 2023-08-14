from typing import List, Union
import os
import configparser
from pathlib import Path
import warnings

from poli.core.abstract_problem_factory import AbstractProblemFactory

from poli.core.util.abstract_observer import AbstractObserver
from poli.core.util.objective_management.make_run_script import (
    make_run_script,
    make_observer_script,
)

_DEFAULT = "DEFAULT"
_OBSERVER = "observer"
_RUN_SCRIPT_LOCATION = "run_script_location"

HOME_DIR = Path.home().resolve()
(HOME_DIR / ".poli_objectives").mkdir(exist_ok=True)

# config_file = os.path.join(os.path.dirname(__file__), "..", "config.rc")
config_file = str(HOME_DIR / ".poli_objectives" / "config.rc")
config = configparser.ConfigParser(defaults={_OBSERVER: ""})
ls = config.read(config_file)
# if len(ls) == 0:
#     warnings.warn("Could not find configuration file: %s" % config_file)


def set_observer(
    observer: AbstractObserver,
    conda_environment_location: str = None,
    python_paths: List[str] = None,
):
    run_script_location = make_observer_script(
        observer, conda_environment_location, python_paths
    )
    set_observer_run_script(run_script_location)


def set_observer_run_script(script_file_name: str) -> None:
    """
    Sets a run_script to be called on observer instantiation.
    VERY IMPORTANT: the observer script MUST accept port and password as arguments
    :param script_file_name:
        path to the script
    """
    # VERY IMPORTANT: the observer script MUST accept port and password as arguments
    config[_DEFAULT][_OBSERVER] = script_file_name
    _write_config()


def delete_observer_run_script() -> str:
    location = config[_DEFAULT][_OBSERVER]  # no need to copy
    config[_DEFAULT][_OBSERVER] = ""
    _write_config()
    return location


def register_problem(
    problem_factory: AbstractProblemFactory,
    conda_environment_name: Union[str, Path] = None,
    python_paths: List[str] = None,
    force: bool = False,
    **kwargs,
):
    if "conda_environment_location" in kwargs:
        conda_environment_name = kwargs["conda_environment_location"]

    problem_name = problem_factory.get_setup_information().get_problem_name()
    if problem_name not in config.sections():
        config.add_section(problem_name)
    elif not force:
        # If force is false, we warn the user and ask for confirmation
        user_input = input(
            f"Problem {problem_name} already exists. "
            f"Do you want to overwrite it? (y/[n]) "
        )
        if user_input.lower() != "y":
            raise ValueError(
                f"Problem {problem_name} already exists. "
                f"Use force=True to overwrite."
            )

        warnings.warn(f"Problem {problem_name} already exists. Overwriting.")

    run_script_location = make_run_script(
        problem_factory, conda_environment_name, python_paths, **kwargs
    )
    config[problem_name][_RUN_SCRIPT_LOCATION] = run_script_location
    _write_config()


def delete_problem(problem_name: str):
    config.remove_section(problem_name)
    _write_config()


def get_problems() -> List[str]:
    problems = config.sections()
    # problems.remove(_DEFAULT)  # no need to remove default section
    return problems


def _write_config():
    with open(config_file, "w+") as configfile:
        config.write(configfile)
