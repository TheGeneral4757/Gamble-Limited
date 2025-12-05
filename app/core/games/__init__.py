"""Game modules for the casino platform."""

from .slots import SlotsGame, slots_game
from .blackjack import BlackjackGame, blackjack_game
from .roulette import RouletteGame, roulette_game
from .plinko import PlinkoGame, plinko_game
from .coinflip import CoinflipGame, coinflip_game

__all__ = [
    "SlotsGame", "slots_game",
    "BlackjackGame", "blackjack_game",
    "RouletteGame", "roulette_game",
    "PlinkoGame", "plinko_game",
    "CoinflipGame", "coinflip_game",
]
