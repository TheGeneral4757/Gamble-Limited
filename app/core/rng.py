import secrets
import random


class TrueRNG:
    """
    A wrapper around Python's `secrets` module to provide cryptographically strong
    random numbers, suitable for casino game logic.
    """

    @staticmethod
    def random_float() -> float:
        """Returns a random float in the range [0.0, 1.0)."""
        # secrets.randbelow(n) returns [0, n). We use a large integer range to approximate a float.
        precision = 10**12
        return secrets.randbelow(precision) / precision

    @staticmethod
    def random_int(min_val: int, max_val: int) -> int:
        """Returns a random integer in the range [min_val, max_val] (inclusive)."""
        # secrets.randbelow(n) returns [0, n). So we need (max - min + 1)
        if min_val > max_val:
            raise ValueError("min_val must be less than or equal to max_val")
        return min_val + secrets.randbelow(max_val - min_val + 1)

    @staticmethod
    def random_choice(options: list):
        """Returns a random element from a non-empty sequence."""
        if not options:
            raise IndexError("Cannot choose from an empty sequence")
        return secrets.choice(options)

    @staticmethod
    def shuffle(deck: list) -> list:
        """Returns a new list with elements shuffled using cryptographically strong randomness."""
        # SystemRandom uses os.urandom(), which is suitable for crypto
        shuffled_deck = deck[:]
        random.SystemRandom().shuffle(shuffled_deck)
        return shuffled_deck


rng = TrueRNG()
