"""
This is the minimal example of how to register
a problem factory, which allows for creating
instances of the problem: the objective function,
the initial point, and its first evaluation.
"""
from typing import Tuple
from string import ascii_uppercase

import numpy as np

from poli.core.abstract_black_box import AbstractBlackBox
from poli.core.abstract_problem_factory import AbstractProblemFactory
from poli.core.problem_setup_information import ProblemSetupInformation


class OurAlohaBlackBox(AbstractBlackBox):
    def __init__(self, info: ProblemSetupInformation, batch_size: int = None):
        super().__init__(info, batch_size)

    # The only method you have to define
    def _black_box(self, x: np.ndarray, context: dict = None) -> np.ndarray:
        matches = x == np.array(["A", "L", "O", "H", "A"])
        return np.sum(matches, axis=1, keepdims=True)


class OurAlohaProblemFactory(AbstractProblemFactory):
    def get_setup_information(self) -> ProblemSetupInformation:
        # The alphabet: ["A", "B", "C", ...]
        alphabet = list(ascii_uppercase)

        return ProblemSetupInformation(
            name="our_aloha",
            max_sequence_length=5,
            aligned=True,
            alphabet=alphabet,
        )

    def create(self, seed: int = 0) -> Tuple[AbstractBlackBox, np.ndarray, np.ndarray]:
        problem_info = self.get_setup_information()
        f = OurAlohaBlackBox(info=problem_info)
        x0 = np.array([["A", "L", "O", "O", "F"]])

        return f, x0, f(x0)


if __name__ == "__main__":
    from poli.core.registry import register_problem

    # Once we have created a simple conda enviroment
    # (see the environment.yml file in this folder),
    # we can register our problem s.t. it uses
    # said conda environment.
    aloha_problem_factory = OurAlohaProblemFactory()
    register_problem(
        aloha_problem_factory,
        conda_environment_name="poli_aloha_problem",
    )
