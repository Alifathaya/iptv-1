"""Interface pipeline: setiap tahap module terpisah dengan kontrak yang sama."""
import numpy as np


class StageResult:
    def __init__(self, image: np.ndarray, notes: dict):
        self.image = image
        self.notes = notes  # dicatat ke cost-log, tanpa data pribadi


class Stage:
    name = "base"

    def run(self, image: np.ndarray, ctx: dict) -> StageResult:
        raise NotImplementedError
