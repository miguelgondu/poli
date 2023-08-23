"""
This script registers FoldX stability as an objective function.
"""
from pathlib import Path
from typing import Dict, List, Tuple
from time import time
from uuid import uuid4


import numpy as np

from Bio.SeqUtils import seq1

from poli.core.abstract_black_box import AbstractBlackBox
from poli.core.abstract_problem_factory import AbstractProblemFactory
from poli.core.problem_setup_information import ProblemSetupInformation

from poli.core.util.proteins.pdb_parsing import (
    parse_pdb_as_residue_strings,
    parse_pdb_as_residues,
)
from poli.core.util.proteins.defaults import ENCODING
from poli.core.util.proteins.mutations import mutations_from_wildtype_and_mutant
from poli.core.util.proteins.foldx import FoldxInterface

# This is the folder where all the files
# generated by FoldX will be stored.
# Feel free to change it if you want
# to keep the files somewhere else.
# An alternative is e.g. TMP_PATH = THIS_DIR
# TODO: what happens if the user is on Windows?
# TMP_PATH = THIS_DIR / "tmp"
TMP_PATH = Path("/tmp").resolve()


class FoldXSASABlackBox(AbstractBlackBox):
    def __init__(
        self,
        L: int,
        wildtype_pdb_file: Path,
        alphabet: Dict[str, int],
        experiment_id: str = None,
    ):
        super().__init__(L)
        self.alphabet = alphabet
        self.decoding = {v: k for k, v in self.alphabet.items()}

        if isinstance(wildtype_pdb_file, str):
            wildtype_pdb_file = Path(wildtype_pdb_file.strip())

        self.wildtype_pdb_file = wildtype_pdb_file

        self.wildtype_residues = parse_pdb_as_residues(wildtype_pdb_file)
        self.wildtype_amino_acids = parse_pdb_as_residue_strings(wildtype_pdb_file)
        self.wildtype_residue_string = "".join(self.wildtype_amino_acids)

        if experiment_id is None:
            experiment_id = f"{int(time())}_{str(uuid4())[:8]}"
        self.experiment_id = experiment_id

    def mutations_from_wildtype(self, mutated_residue_string: str) -> List[str]:
        """
        Since foldx expects an individual_list.txt file of mutations,
        this function computes the Levenshtein distance between
        the wildtype residue string and the mutated residue string,
        keeping track of the replacements.

        This method returns a list of strings which are to be written
        in a single line of individual_list.txt.
        """
        return mutations_from_wildtype_and_mutant(
            self.wildtype_residues, mutated_residue_string
        )

    def create_working_directory(self) -> Path:
        """
        TODO: document.
        """

        working_dir = TMP_PATH / "foldx_tmp_files" / self.experiment_id
        working_dir.mkdir(exist_ok=True, parents=True)

        return working_dir

    def _black_box(self, x: np.ndarray, context: None) -> np.ndarray:
        """
        Runs the given input x and pdb files provided
        in the context through FoldX and returns the
        total energy score.

        Since the goal is MINIMIZING the energy,
        we return the negative of the total energy.

        After the initial call, let's assume that
        the subsequent calls are about mutating
        the wildtype sequence. From then onwards,
        the context should contain
        - wildtype_pdb_file
        - path_to_mutation_list

        To accomodate for the initial call, if the
        path_to_mutation_list is not provided (or
        if it's None), we assume that we're supposed
        to evaluate the energy of the wildtype sequence.
        """
        # Check if the context is valid
        # delete_working_dir = context["delete_working_dir"]
        # wildtype_pdb_file = context["wildtype_pdb_file"]
        wildtype_pdb_file = self.wildtype_pdb_file

        # Create a working directory for this function call
        working_dir = self.create_working_directory()

        # Given that x, we simply define the
        # mutations to be made as a mutation_list.txt
        # file.
        mutations_as_strings = [
            "".join([self.decoding[integer] for integer in x_i]) for x_i in x
        ]

        foldx_interface = FoldxInterface(working_dir)
        sasa_score = foldx_interface.compute_sasa(
            pdb_file=wildtype_pdb_file,
            mutations=mutations_as_strings,
        )

        return np.array([sasa_score]).reshape(-1, 1)


class FoldXSASAProblemFactory(AbstractProblemFactory):
    def get_setup_information(self) -> ProblemSetupInformation:
        """
        TODO: document
        """
        alphabet = ENCODING

        return ProblemSetupInformation(
            name="foldx_sasa",
            max_sequence_length=np.inf,
            alphabet=alphabet,
            aligned=False,
        )

    def create(
        self,
        seed: int = 0,
        wildtype_pdb_path: Path = None,
        alphabet: Dict[str, int] = None,
    ) -> Tuple[AbstractBlackBox, np.ndarray, np.ndarray]:
        L = self.get_setup_information().get_max_sequence_length()
        if wildtype_pdb_path is None:
            raise ValueError(
                "Missing required argument wildtype_pdb_path. "
                "Did you forget to pass it to create()?"
            )

        if isinstance(wildtype_pdb_path, str):
            wildtype_pdb_path = Path(wildtype_pdb_path.strip())
        elif isinstance(wildtype_pdb_path, Path):
            pass
        else:
            raise ValueError(
                f"wildtype_pdb_path must be a string or a Path. Received {type(wildtype_pdb_path)}"
            )

        if alphabet is None:
            # We use the default alphabet.
            # See ENCODING in foldx_utils.py
            alphabet = self.get_setup_information().get_alphabet()

        f = FoldXSASABlackBox(L, wildtype_pdb_path, alphabet)

        wildtype_residues = parse_pdb_as_residues(wildtype_pdb_path)
        wildtype_amino_acids = [
            seq1(residue.get_resname()) for residue in wildtype_residues
        ]

        x0 = np.array(
            [ENCODING[amino_acid] for amino_acid in wildtype_amino_acids]
        ).reshape(1, -1)

        f_0 = f(x0)

        return f, x0, f_0


if __name__ == "__main__":
    from poli.core.registry import register_problem

    foldx_problem_factory = FoldXSASAProblemFactory()
    register_problem(
        foldx_problem_factory,
        conda_environment_name="poli__protein",
    )
