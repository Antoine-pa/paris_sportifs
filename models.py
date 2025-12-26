"""
Models communs pour les scrapers de paris sportifs
Ces classes sont partagées entre tous les bookmakers scrappés
"""
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class Match:
    """Représente un match avec ses cotes 1X2
    
    Cette classe est commune à tous les bookmakers.
    """
    id: str
    competition: str
    home_team: str
    away_team: str
    date: str
    odds_home: float
    odds_draw: float
    odds_away: float
    bookmaker: str = ""  # Nom du bookmaker (Betclic, Winamax, etc.)
    url: str = ""
    sport: str = "football"  # Par défaut football
    
    @property
    def min_odds(self) -> float:
        """La cote minimale des 3 issues"""
        return min(self.odds_home, self.odds_draw, self.odds_away)
    
    @property
    def max_odds(self) -> float:
        """La cote maximale des 3 issues"""
        return max(self.odds_home, self.odds_draw, self.odds_away)
    
    @property
    def guaranteed_profit(self) -> float:
        """Profit garanti en € pour 100€ de freebet"""
        return (self.min_odds - 1) * 100
    
    @property
    def best_profit(self) -> float:
        """Meilleur profit possible en €"""
        return (self.max_odds - 1) * 100
    
    @property
    def conversion_rate(self) -> float:
        """Taux de conversion en % (profit garanti / mise totale)"""
        return (self.guaranteed_profit / 300) * 100
    
    def get_assignment(self, num_players: int = 3) -> list:
        """
        Retourne la répartition optimale des paris entre joueurs
        
        Args:
            num_players: Nombre de joueurs (par défaut 3)
        
        Returns:
            Liste de dictionnaires avec joueur, issue, cote, gain
        """
        odds = [
            ("1 - " + self.home_team, self.odds_home),
            ("N - Match Nul", self.odds_draw),
            ("2 - " + self.away_team, self.odds_away)
        ]
        odds.sort(key=lambda x: x[1], reverse=True)
        
        return [
            {
                "joueur": f"Joueur {i+1}", 
                "issue": issue, 
                "cote": odd, 
                "gain": round((odd - 1) * 100, 2)
            }
            for i, (issue, odd) in enumerate(odds[:num_players])
        ]
    
    def to_dict(self) -> dict:
        """Convertit le match en dictionnaire pour JSON"""
        return {
            "id": self.id,
            "competition": self.competition,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "date": self.date,
            "bookmaker": self.bookmaker,
            "sport": self.sport,
            "odds": {
                "1": self.odds_home,
                "X": self.odds_draw,
                "2": self.odds_away
            },
            "profit_garanti": round(self.guaranteed_profit, 2),
            "meilleur_cas": round(self.best_profit, 2),
            "conversion_rate": round(self.conversion_rate, 2),
            "repartition": self.get_assignment(),
            "url": self.url
        }
    
    def __repr__(self) -> str:
        return f"Match({self.home_team} vs {self.away_team}, {self.bookmaker}, cotes: {self.odds_home}/{self.odds_draw}/{self.odds_away})"


@dataclass 
class ScraperResult:
    """Résultat d'un scraping avec métadonnées"""
    matches: List[Match] = field(default_factory=list)
    bookmaker: str = ""
    status: str = "success"  # success, error, partial
    message: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_seconds: float = 0.0
    
    @property
    def count(self) -> int:
        return len(self.matches)
    
    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "bookmaker": self.bookmaker,
            "message": self.message,
            "count": self.count,
            "timestamp": self.timestamp,
            "duration_seconds": round(self.duration_seconds, 2),
            "matches": [m.to_dict() for m in self.matches]
        }


def display_matches(matches: List[Match], limit: int = 20):
    """Affiche les matchs de manière formatée"""
    if not matches:
        print("\n❌ Aucun match disponible")
        return
    
    # Trier par profit garanti décroissant
    sorted_matches = sorted(matches, key=lambda m: m.min_odds, reverse=True)[:limit]
    
    print("\n" + "=" * 80)
    print(f"🏆 TOP {len(sorted_matches)} MATCHS POUR VOS 3 FREEBETS DE 100€")
    print("=" * 80)
    
    for i, match in enumerate(sorted_matches, 1):
        print(f"\n{'─' * 80}")
        print(f"#{i:2d} | 💰 +{match.guaranteed_profit:.0f}€ ({match.conversion_rate:.1f}%)")
        print(f"    ⚽ {match.home_team} vs {match.away_team}")
        print(f"    🏆 {match.competition} | 📚 {match.bookmaker}")
        print(f"    📊 Cotes: 1={match.odds_home:.2f} | X={match.odds_draw:.2f} | 2={match.odds_away:.2f}")
        
        print(f"    📋 Répartition:")
        for p in match.get_assignment():
            print(f"       {p['joueur']}: {p['issue']} @ {p['cote']:.2f} → +{p['gain']:.0f}€")
    
    if sorted_matches:
        best = sorted_matches[0]
        print("\n" + "=" * 80)
        print(f"🎯 MEILLEUR: {best.home_team} vs {best.away_team} ({best.bookmaker})")
        print(f"   ✅ PROFIT GARANTI: +{best.guaranteed_profit:.0f}€")
        print("=" * 80)
