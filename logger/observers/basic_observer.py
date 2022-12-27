import numpy as np

from logger.observers.rudimentary_observer import RudimentaryObserver


class BasicObserver(RudimentaryObserver):
    def observe(self, x: np.ndarray, y: np.ndarray) -> None:
        self.logger.log({
            HD_PREV: torch.sum((sequences[-2] - next_sequence) != 0),
            HD_WT: torch.sum((wt - next_sequence) != 0),
            HD_MIN: torch.min(torch.sum(torch.cat(sequences[:-1]) - next_sequence != 0, dim=1))
            }, step=self.step)
        super().observe(x, y)
