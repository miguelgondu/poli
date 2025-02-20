"""
Assuming that 'aloha' is not a registered problem,
calling the objective_factory.create with that name
will
1. notice that the aloha problem is not registered,
2. discover that there is an aloha problem in our
   objective_repository,
3. create a conda environment from the environment.yml
    file in the aloha folder,
4. run the run.py file in the aloha folder, registering
    the problem in the config file.
"""

from poli import objective_factory

problem_info, f, x0, y0, run_info = objective_factory.create(
    name="aloha",
    caller_info=None,
    observer=None,
    seed=0,
)

print(x0, y0)
