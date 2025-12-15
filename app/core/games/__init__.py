"""Game modules for the casino platform."""

from .slots import SlotsGame, slots_game
from .blackjack import BlackjackGame, blackjack_game
from .roulette import RouletteGame, roulette_game
from .plinko import PlinkoGame, plinko_game
from .coinflip import CoinflipGame, coinflip_game
from .scratch_cards import ScratchCardsGame, scratch_cards_game
from .highlow import HighLowGame, highlow_game
from .dice import DiceGame, dice_game
from .number_guess import NumberGuessGame, number_guess_game
from .lottery import LotterySystem, lottery_system

__all__ = [
    "SlotsGame",
    "slots_game",
    "BlackjackGame",
    "blackjack_game",
    "RouletteGame",
    "roulette_game",
    "PlinkoGame",
    "plinko_game",
    "CoinflipGame",
    "coinflip_game",
    "ScratchCardsGame",
    "scratch_cards_game",
    "HighLowGame",
    "highlow_game",
    "DiceGame",
    "dice_game",
    "NumberGuessGame",
    "number_guess_game",
    "LotterySystem",
    "lottery_system",
]
