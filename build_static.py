"""
Script de génération de site statique pour GitHub Pages.
Ce script remplace app.py dans le contexte GitHub Actions.
Il lance le scraping, compile les données et génère un fichier 'index.html' autonome.
"""
import os
import sys
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Imports du projet
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pmu.scraper import PMUScraper
from winamax.scraper import WinamaxScraper
from flask import render_template # On utilise Jinja de Flask ou Jinja2 directement
from jinja2 import Environment, FileSystemLoader

def scrape_data():
    """Lance le scraping parallèle"""
    results = {'pmu': None, 'winamax': None}
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(run_scraper, 'pmu'): 'pmu',
            executor.submit(run_scraper, 'winamax'): 'winamax'
        }
        for future in futures:
            bm = futures[future]
            try:
                results[bm] = future.result()
            except Exception as e:
                print(f"❌ Error scraping {bm}: {e}")
                results[bm] = {'count_2p': 0, 'count_3p': 0, 'matches_2p': [], 'matches_3p': [], 'error': str(e)}
    
    return results

def run_scraper(bookmaker):
    """Logique de scraping adaptée de app.py mais sans cache"""
    if bookmaker == 'pmu':
        scraper = PMUScraper(headless=True, fast_mode=True)
    else:
        scraper = WinamaxScraper(headless=True, fast_mode=True)
    
    result = scraper.scrape()
    
    matches_3p = []
    matches_2p = []
    sports_2p = ['basketball', 'tennis', 'basket', 'volley', 'mma', 'boxe']
    
    for m in result.matches:
        sport_lower = (m.sport or m.competition or '').lower()
        is_2p = any(s in sport_lower for s in sports_2p) or m.odds_draw < 1.05 or m.odds_draw > 50
        
        match_data = m.to_dict() # Utilise la méthode native du modèle
        
        # On s'assure que les champs calculés sont présents (déjà fait par to_dict mais recheck conversion)
        if 'conversion_rate' not in match_data:
             match_data['conversion_rate'] = m.conversion_rate
        
        # Ajout attribution pour affichage facile
        if is_2p:
            match_data['assignment'] = [
                {'joueur': 'Joueur 1', 'issue': f"1 - {m.home_team}", 'cote': m.odds_home, 'gain': round((m.odds_home - 1) * 100, 2)},
                {'joueur': 'Joueur 2', 'issue': f"2 - {m.away_team}", 'cote': m.odds_away, 'gain': round((m.odds_away - 1) * 100, 2)},
            ]
            match_data['assignment'].sort(key=lambda x: x['cote'], reverse=True)
            matches_2p.append(match_data)
        else:
            match_data['assignment'] = m.get_assignment()
            matches_3p.append(match_data)
    
    # Tri
    matches_3p.sort(key=lambda x: x['conversion_rate'], reverse=True)
    matches_2p.sort(key=lambda x: x['conversion_rate'], reverse=True)
    
    return {
        'matches_3p': matches_3p,
        'matches_2p': matches_2p,
        'count_3p': len(matches_3p),
        'count_2p': len(matches_2p),
        'timestamp': datetime.now().strftime("%d/%m/%Y %H:%M"),
        'status': 'success'
    }

def generate_html(data):
    """Génère le HTML final"""
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('static_index.html')
    
    # On passe les données en JSON string pour que le JS puisse les utiliser
    # Ou mieux, on fait le rendu directement des blocs. 
    # Pour garder le JS de tri/tabs existant, on va injecter tout le data en variable JS globale.
    
    output = template.render(
        last_update=datetime.now().strftime("%d/%m/%Y à %H:%M"),
        initial_data_pmu=json.dumps(data['pmu']),
        initial_data_winamax=json.dumps(data['winamax'])
    )
    
    # Écrire le fichier index.html à la racine pour GitHub Pages
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(output)
    print("✅ Fichier index.html généré avec succès !")

if __name__ == "__main__":
    print("🚀 Démarrage de la génération statique...")
    data = scrape_data()
    generate_html(data)
