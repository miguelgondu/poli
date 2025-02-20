"""
This test module contains all the different instructions
on how to run the different objective functions that are
available poli's objective repository.
"""


def test_white_noise_example():
    import numpy as np
    from poli import objective_factory

    # How to create
    problem_info, f, x0, y0, run_info = objective_factory.create(name="white_noise")

    # Example input:
    x = np.array([["1", "2", "3"]])  # must be of shape [b, L], in this case [1, 3].

    # Querying:
    print(f(x))


def test_aloha_example():
    import numpy as np
    from poli import objective_factory

    # How to create
    problem_info, f, x0, y0, run_info = objective_factory.create(name="aloha")

    # Example input:
    x = np.array(
        [["A", "L", "O", "O", "F"]]
    )  # must be of shape [b, L], in this case [1, 3].

    # Querying:
    y = f(x)
    print(y)  # Should be 3 (A, L, and the first O).
    assert np.isclose(y, 3).all()


def test_qed_example():
    from pathlib import Path
    import numpy as np
    from poli import objective_factory

    # The path to your alphabet
    THIS_DIR = Path(__file__).parent.resolve()
    path_to_alphabet = THIS_DIR / "alphabet_selfies.json"

    # How to create
    problem_info, f, x0, y0, run_info = objective_factory.create(
        name="rdkit_qed",
        path_to_alphabet=path_to_alphabet,
        string_representation="SELFIES",  # it is "SMILES" by default.
        force_register=True,
    )

    # Example input: a single carbon
    x = np.array([[1]])

    # Querying:
    y = f(x)
    print(y)  # Should be close to 0.35978
    assert np.isclose(y, 0.35978494).all()


def test_logp_example():
    from pathlib import Path
    import numpy as np
    from poli import objective_factory

    # The path to your alphabet
    THIS_DIR = Path(__file__).parent.resolve()
    path_to_alphabet = THIS_DIR / "alphabet_selfies.json"

    # How to create
    problem_info, f, x0, y0, run_info = objective_factory.create(
        name="rdkit_logp",
        path_to_alphabet=path_to_alphabet,
        string_representation="SELFIES",  # it is "SMILES" by default.
        force_register=True,
    )

    # Example input: a single carbon
    x = np.array([[1]])

    # Querying:
    y = f(x)
    print(y)  # Should be close to 0.6361
    assert np.isclose(y, 0.6361).all()
