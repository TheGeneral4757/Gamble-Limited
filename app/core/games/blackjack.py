from app.core.rng import rng
from typing import List, Dict, Optional
import uuid
import time

class Card:
    """Represents a playing card."""
    
    SUITS = ["♠", "♥", "♦", "♣"]
    RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    
    def __init__(self, rank: str, suit: str):
        self.rank = rank
        self.suit = suit
    
    @property
    def value(self) -> int:
        """Get the blackjack value of the card."""
        if self.rank in ["J", "Q", "K"]:
            return 10
        elif self.rank == "A":
            return 11  # Ace is 11 by default, adjusted in hand calculation
        else:
            return int(self.rank)
    
    def to_dict(self) -> Dict:
        return {"rank": self.rank, "suit": self.suit, "display": f"{self.rank}{self.suit}"}
    
    def __repr__(self):
        return f"{self.rank}{self.suit}"


class BlackjackHand:
    """Represents a blackjack hand."""
    
    def __init__(self):
        self.cards: List[Card] = []
    
    def add_card(self, card: Card):
        self.cards.append(card)
    
    @property
    def value(self) -> int:
        """Calculate the best hand value, adjusting aces as needed."""
        total = sum(card.value for card in self.cards)
        aces = sum(1 for card in self.cards if card.rank == "A")
        
        # Adjust aces from 11 to 1 if busting
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        
        return total
    
    @property
    def is_bust(self) -> bool:
        return self.value > 21
    
    @property
    def is_blackjack(self) -> bool:
        return len(self.cards) == 2 and self.value == 21
    
    def to_list(self) -> List[Dict]:
        return [card.to_dict() for card in self.cards]


class BlackjackGame:
    """
    Standard Blackjack game logic.
    Supports deal, hit, and stand actions.
    Games expire after 10 minutes to prevent memory leaks.
    """
    
    GAME_TIMEOUT = 600  # 10 minutes
    
    def __init__(self):
        # Active games stored by game_id with timestamps
        self.active_games: Dict[str, Dict] = {}
    
    def _cleanup_old_games(self):
        """Remove games older than timeout."""
        current_time = time.time()
        expired = [
            gid for gid, game in self.active_games.items()
            if current_time - game.get("created_at", 0) > self.GAME_TIMEOUT
        ]
        for gid in expired:
            del self.active_games[gid]
    
    def _create_deck(self) -> List[Card]:
        """Create and shuffle a standard 52-card deck."""
        deck = [Card(rank, suit) for suit in Card.SUITS for rank in Card.RANKS]
        return rng.shuffle(deck)
    
    def _get_game(self, game_id: str) -> Optional[Dict]:
        """Get an active game by ID."""
        self._cleanup_old_games()
        return self.active_games.get(game_id)
    
    def deal(self, bet_amount: float, user_id: str = None) -> Dict:
        """
        Start a new blackjack game.
        Deals 2 cards to player and dealer.
        
        Returns:
            Game state with player hand and dealer's visible card
        """
        self._cleanup_old_games()
        
        game_id = str(uuid.uuid4())[:8]
        deck = self._create_deck()
        
        player_hand = BlackjackHand()
        dealer_hand = BlackjackHand()
        
        # Deal alternating cards
        player_hand.add_card(deck.pop())
        dealer_hand.add_card(deck.pop())
        player_hand.add_card(deck.pop())
        dealer_hand.add_card(deck.pop())
        
        # Store game state
        game_state = {
            "deck": deck,
            "player_hand": player_hand,
            "dealer_hand": dealer_hand,
            "bet": bet_amount,
            "status": "playing",
            "user_id": user_id,
            "created_at": time.time(),
        }
        
        # Check for player blackjack
        if player_hand.is_blackjack:
            # Check if dealer also has blackjack
            if dealer_hand.is_blackjack:
                game_state["status"] = "complete"
                result = self._finalize_game(game_id, game_state, "push", bet_amount)
                return result
            else:
                game_state["status"] = "blackjack"
                payout = bet_amount * 2.5  # 3:2 payout
                result = self._finalize_game(game_id, game_state, "blackjack", payout)
                return result
        
        # Check for dealer blackjack (insurance would go here in full implementation)
        if dealer_hand.is_blackjack:
            game_state["status"] = "complete"
            result = self._finalize_game(game_id, game_state, "dealer_blackjack", 0)
            return result
        
        self.active_games[game_id] = game_state
        
        return {
            "game_id": game_id,
            "player_hand": player_hand.to_list(),
            "player_value": player_hand.value,
            "dealer_up_card": dealer_hand.cards[0].to_dict(),
            "dealer_hidden": True,
            "status": "playing",
            "bet": bet_amount,
        }
    
    def hit(self, game_id: str, user_id: str = None) -> Dict:
        """
        Draw another card for the player.
        
        Returns:
            Updated game state
        """
        game = self._get_game(game_id)
        if not game:
            return {"error": "Game not found or expired", "game_id": game_id, "status": "error"}
        
        if game["status"] != "playing":
            return {"error": "Game already completed", "game_id": game_id, "status": "error"}
        
        # Verify user owns this game
        if user_id and game.get("user_id") and game["user_id"] != user_id:
            return {"error": "This is not your game", "game_id": game_id, "status": "error"}
        
        # Check if deck is empty (shouldn't happen in normal play)
        if not game["deck"]:
            return {"error": "No cards remaining", "game_id": game_id, "status": "error"}
        
        # Draw a card
        card = game["deck"].pop()
        game["player_hand"].add_card(card)
        
        player_hand = game["player_hand"]
        
        # Check for bust
        if player_hand.is_bust:
            return self._finalize_game(game_id, game, "bust", 0)
        
        # Check for 21 (auto-stand)
        if player_hand.value == 21:
            return self.stand(game_id, user_id)
        
        return {
            "game_id": game_id,
            "player_hand": player_hand.to_list(),
            "player_value": player_hand.value,
            "dealer_up_card": game["dealer_hand"].cards[0].to_dict(),
            "dealer_hidden": True,
            "status": "playing",
            "new_card": card.to_dict(),
            "bet": game["bet"],
        }
    
    def stand(self, game_id: str, user_id: str = None) -> Dict:
        """
        Player stands. Dealer plays out their hand.
        
        Returns:
            Final game result
        """
        game = self._get_game(game_id)
        if not game:
            return {"error": "Game not found or expired", "game_id": game_id, "status": "error"}
        
        if game["status"] != "playing":
            return {"error": "Game already completed", "game_id": game_id, "status": "error"}
        
        # Verify user owns this game
        if user_id and game.get("user_id") and game["user_id"] != user_id:
            return {"error": "This is not your game", "game_id": game_id, "status": "error"}
        
        dealer_hand = game["dealer_hand"]
        player_hand = game["player_hand"]
        deck = game["deck"]
        bet = game["bet"]
        
        # Dealer draws until 17 or higher
        while dealer_hand.value < 17 and deck:
            dealer_hand.add_card(deck.pop())
        
        # Determine winner
        player_val = player_hand.value
        dealer_val = dealer_hand.value
        
        if dealer_hand.is_bust:
            outcome = "dealer_bust"
            payout = bet * 2
        elif player_val > dealer_val:
            outcome = "win"
            payout = bet * 2
        elif player_val < dealer_val:
            outcome = "lose"
            payout = 0
        else:
            outcome = "push"
            payout = bet  # Return original bet
        
        return self._finalize_game(game_id, game, outcome, payout)
    
    def _finalize_game(self, game_id: str, game: Dict, outcome: str, payout: float) -> Dict:
        """Finalize and clean up a game."""
        result = {
            "game_id": game_id,
            "player_hand": game["player_hand"].to_list(),
            "player_value": game["player_hand"].value,
            "dealer_hand": game["dealer_hand"].to_list(),
            "dealer_value": game["dealer_hand"].value,
            "dealer_hidden": False,
            "outcome": outcome,
            "payout": round(payout, 2),
            "bet": game["bet"],
            "status": "complete",
        }
        
        # Remove from active games
        if game_id in self.active_games:
            del self.active_games[game_id]
        
        return result
    
    def get_active_game_count(self) -> int:
        """Get count of active games (for admin)."""
        self._cleanup_old_games()
        return len(self.active_games)


# Singleton instance
blackjack_game = BlackjackGame()
