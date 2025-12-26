"""
Scraper PMU Sport - Récupère les cotes depuis parisportif.pmu.fr avec Selenium + BeautifulSoup
Ce module est spécifique à PMU Sport.
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


class PMUScraper:
    """
    Scraper pour parisportif.pmu.fr avec Selenium + BeautifulSoup
    
    PMU offre un remboursement en CASH (pas freebets) ce qui est optimal.
    """
    
    BOOKMAKER_NAME = "PMU Sport"
    BASE_URL = "https://parisportif.pmu.fr"
    
    SPORTS_1X2 = {
        "Football": "/pari/sport/1",
        # "Rugby": "/pari/sport/5",
        # "Hockey": "/pari/sport/13",
    }
    
    # Sports 1-2 (2 joueurs) - Basketball, Tennis
    SPORTS_1_2 = {
        # "Basketball": "/pari/sport/2",
        # "Tennis": "/pari/sport/9",
    }
    
    # Ancien nom pour compatibilité
    FOOTBALL_PAGES = {
        "Football": "/pari/sport/1",
    }
    
    def __init__(self, headless: bool = True, fast_mode: bool = True):
        """Initialise le scraper PMU Sport"""
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
        
        # Adaptation Raspberry Pi / ARM
        if os.path.exists("/usr/bin/chromedriver"):
            service = Service("/usr/bin/chromedriver")
        else:
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

        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        })
        
        return driver
    
    def _start_driver(self):
        if self.driver is None:
            self.driver = self._create_driver()
    
    def _stop_driver(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def _accept_cookies(self):
        """Accepte les cookies PMU"""
        if self.cookies_accepted:
            return
        
        try:
            buttons = self.driver.find_elements(By.XPATH, 
                "//button[contains(text(), 'accepter') or contains(text(), 'Accepter') or contains(text(), 'Tout accepter')]")
            
            for btn in buttons:
                try:
                    if 'accepter' in btn.text.lower():
                        btn.click()
                        self.cookies_accepted = True
                        time.sleep(2)
                        break
                except:
                    pass
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
            
            # Scraper tous les sports 1X2 et 1-2
            sports_to_scrape = {**self.SPORTS_1X2, **self.SPORTS_1_2}
            for sport_name, sport_path in sports_to_scrape.items():
                matches = self._scrape_page(sport_name, sport_path)
                
                new_count = 0
                for match in matches:
                    match.sport = sport_name
                    if not any(m.home_team == match.home_team and m.away_team == match.away_team for m in all_matches):
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
        return self.scrape().matches
    
    def _scrape_page(self, name: str, path: str) -> List[Match]:
        """Scrape une page PMU"""
        matches = []
        
        try:
            url = f"{self.BASE_URL}{path}"
            self.driver.get(url)
            time.sleep(3)  # Réduit de 5 à 3
            self._accept_cookies()
            time.sleep(3)  # Réduit de 5 à 3
            
            # Scroll pour charger plus de matchs
            for _ in range(4):  # Réduit de 5 à 4
                self.driver.execute_script('window.scrollBy(0, 1000);')
                time.sleep(0.5)  # Réduit de 1 à 0.5
            
            # Récupérer le texte brut
            text = self.driver.find_element(By.TAG_NAME, 'body').text
            
            matches = self._parse_matches_from_text(text, name)
            print(f"    → {len(matches)} matchs trouvés")
            
        except Exception as e:
            print(f"    ⚠️ Erreur: {str(e)[:50]}")
        
        return matches
    
    def _parse_matches_from_text(self, text: str, competition: str) -> List[Match]:
        """
        Parse les matchs depuis le texte brut de PMU.
        
        Structure PMU:
        Équipe1
        X,XX (cote 1)
        Nul
        X,XX (cote N)
        Équipe2
        X,XX (cote 2)
        """
        matches = []
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        # Pattern pour détecter les cotes (X,XX ou X.XX)
        odds_pattern = re.compile(r'^(\d{1,2}[,\.]\d{2})$')
        
        i = 0
        while i < len(lines) - 6:
            # Chercher une séquence: équipe1, cote, Nul, cote, équipe2, cote
            line = lines[i]
            
            # Vérifier si c'est potentiellement une équipe (pas une cote, pas trop court)
            if (len(line) > 2 and 
                not odds_pattern.match(line) and 
                line.lower() not in ['nul', 'match nul', 'n', '1', '2', 'x'] and
                not re.match(r'^\d+$', line) and
                not 'DÉCEMBRE' in line.upper() and
                not re.match(r'^\d{1,2}h\d{2}$', line)):
                
                # Chercher la structure: équipe1, cote1, Nul, cote2, équipe2, cote3
                try:
                    # Regarder les 6-10 prochaines lignes
                    look_ahead = lines[i:i+10]
                    
                    # Trouver les indices des cotes
                    odds_indices = []
                    for j, la_line in enumerate(look_ahead):
                        if odds_pattern.match(la_line):
                            odds_indices.append(j)
                    
                    # On a besoin d'au moins 2 cotes
                    if len(odds_indices) >= 2:
                        # Cas 3 cotes (1N2)
                        has_nul = False
                        if len(odds_indices) >= 3:
                            # Vérifier qu'il y a "Nul" entre les cotes 1 et 2, ou 2 et 3
                            for j in range(odds_indices[0], odds_indices[2] + 1):
                                if j < len(look_ahead) and look_ahead[j].lower() in ['nul', 'match nul']:
                                    has_nul = True
                                    break
                        
                        if has_nul and len(odds_indices) >= 3:
                            # ... (Logique existante pour 3 cotes) ...
                            # Équipe 1: ligne juste avant la 1ère cote
                            home_idx = odds_indices[0] - 1
                            if home_idx >= 0 and not odds_pattern.match(look_ahead[home_idx]):
                                home_team = look_ahead[home_idx]
                                
                                # Équipe 2: ligne juste avant la 3ème cote
                                away_idx = odds_indices[2] - 1
                                if away_idx >= 0 and not odds_pattern.match(look_ahead[away_idx]):
                                    away_team = look_ahead[away_idx]
                                    
                                    if away_team.lower() not in ['nul', 'match nul', 'n']:
                                        odds1 = float(look_ahead[odds_indices[0]].replace(',', '.'))
                                        odds2 = float(look_ahead[odds_indices[1]].replace(',', '.'))
                                        odds3 = float(look_ahead[odds_indices[2]].replace(',', '.'))
                                        
                                        if all(1.01 <= o <= 100 for o in [odds1, odds2, odds3]):
                                            if home_team != away_team and len(home_team) > 2 and len(away_team) > 2:
                                                # Normalisation ID
                                                h_clean = home_team.lower().strip()
                                                a_clean = away_team.lower().strip()
                                                teams_sorted = sorted([h_clean, a_clean])
                                                match_id = f"pmu_{teams_sorted[0][:10]}_{teams_sorted[1][:10]}"
                                                
                                                match = Match(
                                                    id=match_id, competition=competition, home_team=home_team[:40], away_team=away_team[:40],
                                                    date="", odds_home=odds1, odds_draw=odds2, odds_away=odds3, bookmaker=self.BOOKMAKER_NAME,
                                                    url=self.driver.current_url if self.driver else "")
                                                if not any(m.id == match.id for m in matches):
                                                    matches.append(match)
                                                    i += odds_indices[2]
                        
                        # Cas 2 cotes (1-2)
                        elif len(odds_indices) == 2:
                            # Équipe 1: ligne juste avant la 1ère cote
                            home_idx = odds_indices[0] - 1
                            # Équipe 2: ligne juste avant la 2ème cote
                            away_idx = odds_indices[1] - 1
                            
                            if home_idx >= 0 and away_idx > odds_indices[0]:
                                home_team = look_ahead[home_idx]
                                away_team = look_ahead[away_idx]
                                
                                if (not odds_pattern.match(home_team) and not odds_pattern.match(away_team) and
                                    home_team.lower() not in ['nul', 'match nul'] and away_team.lower() not in ['nul', 'match nul']):
                                    
                                    odds1 = float(look_ahead[odds_indices[0]].replace(',', '.'))
                                    odds2 = float(look_ahead[odds_indices[1]].replace(',', '.'))
                                    
                                    if all(1.01 <= o <= 100 for o in [odds1, odds2]):
                                        # Normalisation ID
                                        h_clean = home_team.lower().strip()
                                        a_clean = away_team.lower().strip()
                                        teams_sorted = sorted([h_clean, a_clean])
                                        match_id = f"pmu_{teams_sorted[0][:10]}_{teams_sorted[1][:10]}"
                                        
                                        match = Match(
                                            id=match_id, competition=competition, home_team=home_team[:40], away_team=away_team[:40],
                                            date="", odds_home=odds1, odds_draw=1.0, odds_away=odds2, bookmaker=self.BOOKMAKER_NAME,
                                            url=self.driver.current_url if self.driver else "")
                                        
                                        if not any(m.home_team == match.home_team and m.away_team == match.away_team for m in matches):
                                            matches.append(match)
                                            i += odds_indices[1]
                except Exception:
                    pass
            
            i += 1
        
        return matches


# ============================================================================
# Fonctions utilitaires exportées
# ============================================================================

def get_best_matches(limit: int = 30) -> List[Match]:
    """Récupère et classe les meilleurs matchs PMU Sport"""
    scraper = PMUScraper(headless=True)
    result = scraper.scrape()
    
    if not result.matches:
        print("\n⚠️ Impossible de scraper PMU Sport.")
        return []
    
    matches = sorted(result.matches, key=lambda m: m.min_odds, reverse=True)
    return matches[:limit]


def get_matches_as_json() -> dict:
    """Retourne les matchs PMU en JSON pour l'API"""
    scraper = PMUScraper(headless=True)
    result = scraper.scrape()
    
    return {
        "bookmaker": "PMU Sport",
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
