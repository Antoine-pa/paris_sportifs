"""
Scraper Winamax - Récupère les cotes depuis winamax.fr avec Selenium + BeautifulSoup
Ce module est spécifique à Winamax.
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
from typing import List, Optional
import time
import sys
import os

# Ajouter le parent au path pour importer models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import Match, ScraperResult, display_matches


class WinamaxScraper:
    """
    Scraper pour winamax.fr avec Selenium + BeautifulSoup
    
    Utilise Chrome headless pour charger la page puis BeautifulSoup
    pour parser le HTML et extraire les cotes 1X2.
    """
    
    BOOKMAKER_NAME = "Winamax"
    BASE_URL = "https://www.winamax.fr"
    
    # Sports 1X2 (3 joueurs) - Football, Rugby, Hockey
    SPORTS_1X2 = {
        "Football": "/paris-sportifs/sports/1",
        "Rugby": "/paris-sportifs/sports/12",
        "Hockey": "/paris-sportifs/sports/4",
    }
    
    # Sports 1-2 (2 joueurs) - Basketball, Tennis
    SPORTS_1_2 = {
        "Basketball": "/paris-sportifs/sports/2",
        "Tennis": "/paris-sportifs/sports/5",
    }
    
    # Ancien nom pour compatibilité
    FOOTBALL_PAGES = {
        "Football": "/paris-sportifs/sports/1",
    }
    
    def __init__(self, headless: bool = True, fast_mode: bool = True):
        """Initialise le scraper Winamax
        
        Args:
            headless: True pour exécuter sans interface graphique
            fast_mode: True pour scraper seulement les pages principales
        """
        self.headless = headless
        self.fast_mode = fast_mode
        self.driver = None
        self.cookies_accepted = False
    
    def _create_driver(self):
        """Crée un driver Chrome avec options anti-détection"""
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        service = Service(ChromeDriverManager().install())
        # Initialisation du driver
        driver = webdriver.Chrome(service=service, options=options)
        
        # Configuration Stealth (Furtivité avancée)
        try:
            from selenium_stealth import stealth
            stealth(driver,
                languages=["fr-FR", "fr"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
            )
        except ImportError:
            print("⚠️ Selenium-stealth non installé, mode standard")

        # Bypass classique supplémentaire
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        })
        
        return driver
    
    def _start_driver(self):
        """Démarre le driver si nécessaire"""
        if self.driver is None:
            self.driver = self._create_driver()
    
    def _stop_driver(self):
        """Arrête le driver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def _accept_cookies(self):
        """Accepte les cookies si la popup apparaît"""
        if self.cookies_accepted:
            return
        
        try:
            # Winamax utilise différents sélecteurs pour les cookies
            cookie_selectors = [
                "//button[contains(text(), 'Tout accepter')]",
                "//button[contains(text(), 'Accepter')]",
                "//button[contains(@class, 'accept')]",
                "//button[@id='tarteaucitronPersonalize2']",
            ]
            
            for selector in cookie_selectors:
                try:
                    cookie_btn = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    cookie_btn.click()
                    self.cookies_accepted = True
                    time.sleep(1)
                    break
                except:
                    continue
        except:
            pass
    
    def scrape(self) -> ScraperResult:
        """Lance le scraping et retourne un ScraperResult"""
        start_time = time.time()
        all_matches = []
        status = "success"
        message = ""
        
        print(f"🔄 Scraping {self.BOOKMAKER_NAME} (mode {'rapide' if self.fast_mode else 'complet'})...")
        
        try:
            self._start_driver()
            
            # Scraper tous les sports 1X2 (foot, rugby, hockey) et 1-2 (basket, tennis)
            sports_to_scrape = {**self.SPORTS_1X2, **self.SPORTS_1_2}
            for sport_name, sport_path in sports_to_scrape.items():
                matches = self._scrape_page(sport_name, sport_path)
                
                new_count = 0
                for match in matches:
                    # Ajouter le sport au match
                    match.sport = sport_name
                    # Éviter les doublons par ID unique (déjà normalisé)
                    if not any(m.id == match.id for m in all_matches):
                        all_matches.append(match)
                        new_count += 1
                
                if new_count > 0:
                    print(f"  ✅ {sport_name}: +{new_count} nouveaux matchs")
            
            message = f"{len(all_matches)} matchs récupérés"
            
        except Exception as e:
            status = "error"
            message = str(e)
            print(f"❌ Erreur: {e}")
        finally:
            self._stop_driver()
        
        duration = time.time() - start_time
        print(f"\n📊 Total: {len(all_matches)} matchs uniques ({duration:.1f}s)")
        
        return ScraperResult(
            matches=all_matches,
            bookmaker=self.BOOKMAKER_NAME,
            status=status,
            message=message,
            duration_seconds=duration
        )
    
    def get_all_matches(self) -> List[Match]:
        """Alias pour compatibilité"""
        return self.scrape().matches
    
    def _scrape_page(self, name: str, path: str) -> List[Match]:
        """Scrape une page Winamax avec Selenium puis parse avec BeautifulSoup"""
        matches = []
        
        try:
            url = f"{self.BASE_URL}{path}"
            self.driver.get(url)
            time.sleep(2)  # Réduit de 3 à 2
            self._accept_cookies()
            time.sleep(1)  # Réduit de 2 à 1
            
            # Scroll pour charger plus de matchs
            self._scroll_page()
            
            # Récupérer le HTML et parser avec BeautifulSoup
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'lxml')
            
            matches = self._parse_matches_with_bs4(soup, name)
            print(f"    → {len(matches)} matchs trouvés")
            
        except Exception as e:
            print(f"    ⚠️ Erreur: {str(e)[:50]}")
        
        return matches
    
    def _scroll_page(self):
        """Scroll la page pour charger plus de contenu"""
        try:
            for _ in range(3):
                self.driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(0.3)  # Réduit de 0.5 à 0.3
        except:
            pass
    
    def _parse_matches_with_bs4(self, soup: BeautifulSoup, competition: str) -> List[Match]:
        """Parse les matchs avec BeautifulSoup - adapté à la structure Winamax"""
        matches = []
        
        # Winamax utilise la classe bet-group-outcome-odd pour les boutons de cotes
        bet_buttons = soup.select('.bet-group-outcome-odd')
        
        if not bet_buttons:
            # Fallback: chercher par classe contenant "odd"
            bet_buttons = soup.select('[class*="odd-button"]')
        
        print(f"    (trouvé {len(bet_buttons)} boutons de cotes)")
        
        # Les cotes sont groupées par 3 (1, N, 2)
        # Remonter de 2 niveaux pour trouver le conteneur des 3 cotes
        processed_grandparents = set()
        
        for bet_btn in bet_buttons:
            # Remonter de 2 niveaux (parent puis grand-parent)
            parent = bet_btn.parent
            if parent:
                grandparent = parent.parent
                if grandparent and id(grandparent) not in processed_grandparents:
                    # Vérifier si le grand-parent contient exactement 2 ou 3 éléments de cotes
                    odds_in_grandparent = grandparent.select('.bet-group-outcome-odd')
                    
                    if len(odds_in_grandparent) in [2, 3]:
                        processed_grandparents.add(id(grandparent))
                        
                        # Extraire le texte complet du grand-parent
                        match = self._parse_match_from_bet_group(grandparent, competition)
                        if match:
                            matches.append(match)
        
        return matches
    
    def _parse_match_from_bet_group(self, elem, competition: str) -> Optional[Match]:
        """Parse un groupe de paris pour extraire le match"""
        try:
            # Récupérer le texte avec séparateurs
            text = elem.get_text('|', strip=True)
            
            if not text or len(text) < 10:
                return None
            
            # Pattern Winamax: "XXX|Équipe1|cote1|Match nul|cote2|Équipe2|cote3"
            # ou parfois: "Équipe1|cote1|N|cote2|Équipe2|cote3"
            
            parts = [p.strip() for p in text.split('|') if p.strip()]
            
            # Trouver les cotes (format X,XX ou X.XX)
            odds_pattern = r'^(\d{1,2}[,\.]\d{1,2})$'
            
            odds_indices = []
            for i, part in enumerate(parts):
                if re.match(odds_pattern, part):
                    odds_indices.append(i)
            
            if len(odds_indices) < 2:
                return None
            
            # Les 2 ou 3 premières cotes trouvées
            odds_values = []
            for idx in odds_indices[:3]:
                val = float(parts[idx].replace(',', '.'))
                if 1.01 <= val <= 100:
                    odds_values.append(val)
            
            if len(odds_values) not in [2, 3]:
                return None
            
            if len(odds_values) == 3:
                odds_home = odds_values[0]
                odds_draw = odds_values[1]
                odds_away = odds_values[2]
            else:
                odds_home = odds_values[0]
                odds_draw = 1.0  # Pas de nul
                odds_away = odds_values[1]
            
            # Trouver les équipes
            # Pattern Winamax 3 issues: "index|équipe1|cote1|Match nul|cote2|équipe2|cote3"
            # Pattern Winamax 2 issues: "index|équipe1|cote1|équipe2|cote2"
            
            first_odds_idx = odds_indices[0]
            # Pour 2 issues, la 2ème cote est à l'index 1
            last_odds_idx = odds_indices[2] if len(odds_indices) >= 3 else odds_indices[1]
            
            # Équipe domicile: juste avant la 1ère cote
            home_team = None
            for i in range(first_odds_idx - 1, -1, -1):
                candidate = parts[i]
                # Ignorer "Match nul", "N", les nombres seuls, et les pourcentages
                if candidate.lower() not in ['match nul', 'n', 'nul', '1', '2', 'x']:
                    if not re.match(r'^[\d,\.%]+$', candidate):  # Exclure aussi les %
                        if len(candidate) > 2:  # Un nom d'équipe a au moins 3 caractères
                            home_team = candidate
                            break
            
            # Équipe extérieur: ENTRE la 1ère et dernière cote utilisée
            # Pour 3 issues: entre cote 2 et cote 3
            # Pour 2 issues: entre cote 1 et cote 2
            away_team = None
            
            if len(odds_values) == 3:
                start_search = odds_indices[1] + 1
                end_search = odds_indices[2]
            else:
                start_search = odds_indices[0] + 1
                end_search = odds_indices[1]

            for i in range(start_search, end_search):
                candidate = parts[i]
                if candidate.lower() not in ['match nul', 'n', 'nul', '1', '2', 'x']:
                    if not re.match(r'^[\d,\.%]+$', candidate):  # Exclure aussi les %
                        if len(candidate) > 2:  # Un nom d'équipe a au moins 3 caractères
                            away_team = candidate
                            break
            
            if not home_team or not away_team:
                return None
            
            # Nettoyer les noms d'équipes
            home_team = home_team[:40].strip()
            away_team = away_team[:40].strip()
            
            if home_team == away_team or len(home_team) < 2 or len(away_team) < 2:
                return None
            
            # Normalisation pour l'ID unique (gestion A vs B / B vs A et clean noms)
            def clean_name(name):
                # Enlever les virgules inversées "Nom, Prénom" -> "Prénom Nom"
                if ',' in name:
                    parts = name.split(',')
                    if len(parts) == 2:
                        return f"{parts[1].strip()} {parts[0].strip()}".lower()
                return name.lower().replace(',', '').strip()
            
            h_clean = clean_name(home_team)
            a_clean = clean_name(away_team)
            
            # ID indépendant de l'ordre domicile/extérieur
            teams_sorted = sorted([h_clean, a_clean])
            match_id = f"winamax_{teams_sorted[0][:10]}_{teams_sorted[1][:10]}"
            
            # Détection et exclusion explicite des paris "Set" ou "Jeu" ou "Point" dans le texte
            # (Heuristique simple: si le texte original contient ces mots, c'est probablement pas le vainqueur du match du tout début)
            full_text = elem.get_text().lower()
            if "set " in full_text or "jeu " in full_text or "point " in full_text or "exact" in full_text:
                # On risque de filtrer trop, mais c'est plus sûr pour éviter les doublons de paris annexes
                # Pour le moment, on se fie au dédoublonnage par ID (on garde le premier trouvé)
                pass 

            return Match(
                id=match_id,
                competition=competition,
                home_team=home_team,
                away_team=away_team,
                date="",
                odds_home=odds_home,
                odds_draw=odds_draw,
                odds_away=odds_away,
                bookmaker=self.BOOKMAKER_NAME,
                url=self.driver.current_url if self.driver else ""
            )
            
        except Exception as e:
            return None


# ============================================================================
# Fonctions utilitaires exportées
# ============================================================================

def get_best_matches(limit: int = 30) -> List[Match]:
    """Récupère et classe les meilleurs matchs Winamax"""
    scraper = WinamaxScraper(headless=True)
    result = scraper.scrape()
    
    if not result.matches:
        print("\n⚠️ Impossible de scraper Winamax.")
        return []
    
    matches = sorted(result.matches, key=lambda m: m.min_odds, reverse=True)
    return matches[:limit]


def get_matches_as_json() -> dict:
    """Retourne les matchs Winamax en JSON pour l'API"""
    scraper = WinamaxScraper(headless=True)
    result = scraper.scrape()
    
    return {
        "bookmaker": "Winamax",
        "status": result.status,
        "message": result.message,
        "count": result.count,
        "timestamp": result.timestamp,
        "duration_seconds": result.duration_seconds,
        "matches": [m.to_dict() for m in sorted(result.matches, key=lambda m: m.min_odds, reverse=True)]
    }


if __name__ == "__main__":
    matches = get_best_matches(20)
    display_matches(matches, limit=20)
