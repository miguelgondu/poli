"""
This is the main file relevant for users who want to run objective functions.
"""
from typing import Callable, Tuple, Any, Dict
import numpy as np
from pathlib import Path
import configparser
import traceback
import logging

from poli.core.abstract_black_box import AbstractBlackBox
from poli.core.abstract_problem_factory import AbstractProblemFactory
from poli.core.problem_setup_information import ProblemSetupInformation
from poli.core.registry import (
    _RUN_SCRIPT_LOCATION,
    _DEFAULT,
    _OBSERVER,
    register_problem_from_repository,
)
from poli.core.util.abstract_observer import AbstractObserver
from poli.core.util.external_observer import ExternalObserver
from poli.core.util.inter_process_communication.process_wrapper import ProcessWrapper

from poli.objective_repository import AVAILABLE_OBJECTIVES, AVAILABLE_PROBLEM_FACTORIES


def load_config():
    HOME_DIR = Path.home().resolve()
    config_file = str(HOME_DIR / ".poli_objectives" / "config.rc")
    config = configparser.ConfigParser(defaults={_OBSERVER: ""})
    ls = config.read(config_file)

    return config


class ExternalBlackBox(AbstractBlackBox):
    def __init__(self, info: ProblemSetupInformation, process_wrapper):
        super().__init__(info)
        self.process_wrapper = process_wrapper

    def _black_box(self, x, context=None):
        self.process_wrapper.send(["QUERY", x, context])
        msg_type, *val = self.process_wrapper.recv()
        if msg_type == "EXCEPTION":
            e, traceback_ = val
            print(traceback_)
            raise e
        elif msg_type == "QUERY":
            y = val[0]

            return y
        else:
            raise ValueError(
                f"Internal error: received {msg_type} when expecting QUERY or EXCEPTION"
            )

    def terminate(self):
        # terminate objective process
        if self.process_wrapper is not None:
            self.process_wrapper.send(["QUIT", None])
            self.process_wrapper.close()  # clean up connection
            self.process_wrapper = None
        # terminate observer
        if self.observer is not None:
            self.observer.finish()
            self.observer = None

    def __getattr__(self, __name: str) -> Any:
        """
        Asks for the attribute of the underlying
        black-box function by sending a message
        to the process w. the msg_type "ATTRIBUTE".
        """
        self.process_wrapper.send(["ATTRIBUTE", __name])
        _, val = self.process_wrapper.recv()
        return val

    def __del__(self):
        self.terminate()

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.terminate()


def __create_from_repository(
    name: str, seed: int = 0, **kwargs_for_factory
) -> Tuple[AbstractBlackBox, np.ndarray, np.ndarray]:
    """
    If the problem is available in AVAILABLE_PROBLEM_FACTORIES
    (i.e. if the user could import all the dependencies directly),
    we create the problem directly. Otherwise, we raise an error.
    """
    if name not in AVAILABLE_PROBLEM_FACTORIES:
        raise ValueError(
            f"Objective function '{name}' is not available in the repository."
        )

    problem_factory = AVAILABLE_PROBLEM_FACTORIES[name]()
    f, x0, y0 = problem_factory.create(seed=seed, **kwargs_for_factory)

    return f, x0, y0


def __create_as_isolated_process(
    name: str,
    seed: int = 0,
    **kwargs_for_factory,
) -> Tuple[AbstractBlackBox, np.ndarray, np.ndarray]:
    """
    If the problem is registered, we create it as an isolated
    process. Otherwise, we raise an error.
    """
    config = load_config()
    if name not in config:
        raise ValueError(f"Objective function '{name}' is not registered. ")

    # start objective process
    # VERY IMPORTANT: the script MUST accept port and password as arguments
    process_wrapper = ProcessWrapper(
        config[name][_RUN_SCRIPT_LOCATION], **kwargs_for_factory
    )
    # TODO: add signal listener that intercepts when proc ends
    # wait for connection from objective process
    # TODO: potential (unlikely) race condition! (process might try to connect before listener is ready!)
    process_wrapper.send(("SETUP", seed))

    msg_type, *msg = process_wrapper.recv()
    if msg_type == "SETUP":
        # Then the instance of the abstract factory
        # was correctly set-up, and
        x0, y0, problem_information = msg
    elif msg_type == "EXCEPTION":
        e, tb = msg
        print(tb)
        raise e
    else:
        raise ValueError(
            f"Internal error: received {msg_type} when expecting SETUP or EXCEPTION"
        )

    f = ExternalBlackBox(problem_information, process_wrapper)

    return f, x0, y0


def __register_objective_if_available(name: str, force_register: bool = False):
    config = load_config()
    if name not in config:
        if name not in AVAILABLE_OBJECTIVES:
            raise ValueError(
                f"Objective function '{name}' is not registered, "
                "and it is not available in the repository."
            )

        # At this point, we know that the function is available
        # in the repository
        if force_register:
            # Then we install it.
            answer = "y"
        else:
            # We ask the user for their confirmation
            answer = input(
                f"Objective function '{name}' is not registered, "
                "but it is available in the repository. Do you "
                "want to install it? (y/[n]): "
            )

        if answer == "y":
            # Register problem
            register_problem_from_repository(name)
            # TODO: change print to logging
            logging.debug(f"Registered the objective from the repository.")
            # Refresh the config
            config = load_config()
        else:
            raise ValueError(
                f"Objective function '{name}' won't be registered. Aborting."
            )


def create(
    name: str,
    seed: int = 0,
    caller_info: dict = None,
    observer: AbstractObserver = None,
    force_register: bool = False,
    force_isolation: bool = False,
    **kwargs_for_factory,
) -> Tuple[ProblemSetupInformation, AbstractBlackBox, np.ndarray, np.ndarray, object]:
    """
    Instantiantes a black-box function.
    :param name:
        The name of the objective function or a shell-script for execution.
    :param seed:
        Information for the objective in case randomization is involved.
    :param caller_info:
        Optional information about the caller that is forwarded to the logger to initialize the run.
    :param observer:
        Optional observer, external observer by default.
    :param force_register:
        If True, then the objective function is registered without asking
        for confirmation, overwriting any previous registration.
    :param force_isolation:
        If True, then the objective function is instantiated as an isolated
        process.
    :return:
        problem_information: a ProblemSetupInformation object holding basic properties about the problem
        f: an objective function that accepts a numpy array and returns a numpy array
        x0: initial inputs
        y0: f(x0)
        observer_info: information from the observer_info about the instantiated run (allows the calling algorithm to connect)
    """
    # If the user can run it with the envionment they currently
    # have, then we do not need to install it.
    if name in AVAILABLE_PROBLEM_FACTORIES and not force_isolation:
        f, x0, y0 = __create_from_repository(name, seed=seed, **kwargs_for_factory)
        problem_info = f.info
        return problem_info, f, x0, y0, None

    # TODO: change prints for logs and warnings.
    # Check if the name is indeed registered, or
    # available in the objective repository
    __register_objective_if_available(name, force_register=force_register)

    # At this point, we know the name is registered.
    # Thus, we should be able to start it as an isolated process
    f, x0, y0 = __create_as_isolated_process(
        name,
        seed=seed,
        **kwargs_for_factory,
    )
    problem_information = f.info

    # instantiate observer (if desired)
    observer_info = None
    if observer is not None:
        observer_info = observer.initialize_observer(
            problem_information, caller_info, x0, y0, seed
        )

    f.set_observer(observer)

    return problem_information, f, x0, y0, observer_info


def start(
    name: str,
    seed: int = 0,
    caller_info: dict = None,
    observer: AbstractObserver = None,
    force_register: bool = False,
    force_isolation: bool = False,
    **kwargs_for_factory,
) -> AbstractBlackBox:
    """
    Works just like create, but it does not run the function on anything, and returns
    only the black-box function.

    One example of running this function:

    ```python
    from poli import objective_factory

    with objective_factory.start(name="aloha") as f:
        x = np.array(["F", "L", "E", "A", "S"]).reshape(1, -1)
        y = f(x)
        print(x, y)
    ```

    If the black-box function is created as an isolated process, then
    it will automatically close when the context manager is closed.
    """
    # Check if we can import the function immediately
    if name in AVAILABLE_PROBLEM_FACTORIES and not force_isolation:
        f, _, _ = __create_from_repository(name, seed=seed, **kwargs_for_factory)
        return f

    # Check if the name is indeed registered, or
    # available in the objective repository
    __register_objective_if_available(name, force_register=force_register)

    # If not, then we create it as an isolated process
    f, _, _ = __create_as_isolated_process(name, seed=seed, **kwargs_for_factory)

    # instantiate observer (if desired)
    if observer is not None:
        observer.initialize_observer(f.info, caller_info, None, None, seed)

    f.set_observer(observer)

    return f
