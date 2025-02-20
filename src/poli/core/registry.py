from typing import List, Union, Dict
import os
import configparser
from pathlib import Path
import warnings
import subprocess

from poli.core.abstract_problem_factory import AbstractProblemFactory

from poli.core.util.abstract_observer import AbstractObserver
from poli.core.util.objective_management.make_run_script import (
    make_run_script,
    make_observer_script,
)

from poli.objective_repository import AVAILABLE_PROBLEM_FACTORIES, AVAILABLE_OBJECTIVES

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
    problem_factory: Union[AbstractProblemFactory, str],
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
            warnings.warn(f"Problem {problem_name} already exists. Not overwriting.")
            return

        warnings.warn(f"Problem {problem_name} already exists. Overwriting.")

    run_script_location = make_run_script(
        problem_factory, conda_environment_name, python_paths, **kwargs
    )
    config[problem_name][_RUN_SCRIPT_LOCATION] = run_script_location
    _write_config()


def register_problem_from_repository(name: str):
    # the name is actually the folder inside
    # poli/objective_repository, so we need
    # to
    # 1. create the environment from the yaml file
    # 2. run the file from said enviroment (since
    #    we can't import the factory: it may have
    #    dependencies that are not installed)

    # Moreover, we should only be doing this
    # if the problem is not already registered.
    PATH_TO_REPOSITORY = (
        Path(__file__).parent.parent / "objective_repository"
    ).resolve()

    if name in config.sections():
        warnings.warn(f"Problem {name} already registered. Skipping")
        return

    # 1. create the environment from the yaml file
    try:
        subprocess.run(
            " ".join(
                [
                    "conda",
                    "env",
                    "create",
                    "-f",
                    str(PATH_TO_REPOSITORY / name / "environment.yml"),
                ]
            ),
            shell=True,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        if "already exists" in e.stderr.decode():
            warnings.warn(f"Environment {name} already exists. Will not create it.")
        else:
            raise e

    # 2. run the file from said enviroment (since
    #    we can't import the factory: it may have
    #    dependencies that are not installed)

    # 2.1. Loading up the yml file to get the name
    # of the environment
    with open(PATH_TO_REPOSITORY / name / "environment.yml", "r") as f:
        # This is a really crude way of doing this,
        # but it works. We should probably use a
        # yaml parser instead, but the idea is to keep
        # the dependencies to a minimum.
        yml = f.read()
        lines = yml.split("\n")
        conda_env_name_line = lines[0]
        assert conda_env_name_line.startswith("name:"), (
            "The first line of the environment.yml file "
            "should be the name of the environment"
        )
        env_name = lines[0].split(":")[1].strip()

    # 2.2. Running the file
    file_to_run = PATH_TO_REPOSITORY / name / "register.py"
    command = " ".join(["conda", "run", "-n", env_name, "python", str(file_to_run)])
    warnings.warn("Running the following command: %s. " % command)
    try:
        subprocess.run(command, check=True, shell=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Found error when running {file_to_run} from environment {env_name}: \n"
            f"{e.stderr.decode()}"
        )


def delete_problem(problem_name: str):
    config.remove_section(problem_name)
    _write_config()


def get_problems(include_repository: bool = False) -> List[str]:
    problems = config.sections()
    # problems.remove(_DEFAULT)  # no need to remove default section

    # We also pad the get_problems() with the problems
    # the user can import already without any problem,
    # i.e. the AVAILABLE_PROBLEM_FACTORIES in the
    # objective_repository
    available_problems = list(AVAILABLE_PROBLEM_FACTORIES.keys())

    if include_repository:
        # We include the problems that the user _could_
        # install from the repo. These are available in the
        # AVAILABLE_OBJECTIVES list.
        available_problems += AVAILABLE_OBJECTIVES

    problems = sorted(list(set(problems + available_problems)))

    return problems


def get_problem_factories() -> Dict[str, AbstractProblemFactory]:
    """
    Returns a dictionary with the problem factories
    """
    return AVAILABLE_PROBLEM_FACTORIES


def _write_config():
    with open(config_file, "w+") as configfile:
        config.write(configfile)
