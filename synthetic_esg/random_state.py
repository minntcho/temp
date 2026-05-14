from __future__ import annotations

import random


def make_random(seed: int) -> random.Random:
    return random.Random(seed)
