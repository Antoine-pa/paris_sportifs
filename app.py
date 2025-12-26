"""
Application Flask pour l'optimisation des paris sportifs
Version optimisée avec parallélisation, cache étendu et pré-chargement
"""
from flask import Flask, render_template, jsonify
from flask_cors import CORS
import sys
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pmu.scraper import PMUScraper
from winamax.scraper import WinamaxScraper
from models import Match

app = Flask(__name__)
app.secret_key = 'paris_sportifs_secret_key_2024'
CORS(app)

# Cache serveur - 30 minutes
_cache = {}
CACHE_DURATION = 1800  # 30 minutes

# Status du pré-chargement
_preload_status = {'pmu': 'pending', 'winamax': 'pending'}
_locks = {
    'pmu': threading.Lock(),
    'winamax': threading.Lock()
}

def get_cached_data(key):
    if key in _cache:
        cached = _cache[key]
        if time.time() - cached['timestamp'] < CACHE_DURATION:
            return cached['data']
    return None


def set_cache_data(key, data):
    _cache[key] = {'data': data, 'timestamp': time.time()}


def scrape_bookmaker(bookmaker):
    """Scrape un bookmaker et retourne les données formatées"""
    global _preload_status
    
    # Vérifier si déjà en cours (bloquer jusqu'à la fin)
    with _locks[bookmaker]:
        # Vérifier le cache une 2ème fois au cas où il aurait été rempli pendant l'attente
        cached = get_cached_data(f"{bookmaker}_all")
        if cached:
            return cached
            
        _preload_status[bookmaker] = 'loading'
        
        try:
            if bookmaker == 'pmu':
                scraper = PMUScraper(headless=True, fast_mode=True)
            else:
                scraper = WinamaxScraper(headless=True, fast_mode=True)
            
            result = scraper.scrape()
            
            # Séparer les matchs
            matches_3p = []
            matches_2p = []
            sports_2p = ['basketball', 'tennis', 'basket', 'volley', 'mma', 'boxe']
            
            for m in result.matches:
                sport_lower = (m.sport or m.competition or '').lower()
                is_2p = any(s in sport_lower for s in sports_2p) or m.odds_draw < 1.05 or m.odds_draw > 50
                
                match_data = {
                    'id': m.id,
                    'home_team': m.home_team,
                    'away_team': m.away_team,
                    'competition': m.competition,
                    'sport': m.sport,
                    'odds_home': m.odds_home,
                    'odds_draw': m.odds_draw,
                    'odds_away': m.odds_away,
                }
                
                if is_2p:
                    min_odds = min(m.odds_home, m.odds_away)
                    match_data['profit_garanti'] = round((min_odds - 1) * 100, 0)
                    match_data['conversion_rate'] = round((min_odds - 1) * 100 / 200 * 100, 1)
                    match_data['assignment'] = [
                        {'joueur': 'Joueur 1', 'issue': f"1 - {m.home_team}", 'cote': m.odds_home, 'gain': round((m.odds_home - 1) * 100, 2)},
                        {'joueur': 'Joueur 2', 'issue': f"2 - {m.away_team}", 'cote': m.odds_away, 'gain': round((m.odds_away - 1) * 100, 2)},
                    ]
                    match_data['assignment'].sort(key=lambda x: x['cote'], reverse=True)
                    matches_2p.append(match_data)
                else:
                    min_odds = min(m.odds_home, m.odds_draw, m.odds_away)
                    match_data['profit_garanti'] = round((min_odds - 1) * 100, 0)
                    match_data['conversion_rate'] = round((min_odds - 1) * 100 / 300 * 100, 1)
                    match_data['assignment'] = m.get_assignment()
                    matches_3p.append(match_data)
            
            # Trier par taux de conversion pour les 3 joueurs aussi (comme demandé)
            matches_3p.sort(key=lambda x: x['conversion_rate'], reverse=True)
            # Trier par taux de conversion pour les 2 joueurs
            matches_2p.sort(key=lambda x: x['conversion_rate'], reverse=True)
            
            response_data = {
                'bookmaker': result.bookmaker,
                'status': result.status,
                'duration': round(result.duration_seconds, 1),
                'from_cache': False,
                'matches_3p': matches_3p[:20],
                'matches_2p': matches_2p[:20],
                'count_3p': len(matches_3p),
                'count_2p': len(matches_2p),
            }
            
            set_cache_data(f"{bookmaker}_all", response_data)
            _preload_status[bookmaker] = 'ready'
            return response_data
            
        except Exception as e:
            _preload_status[bookmaker] = 'error'
            print(f"❌ Erreur scraping {bookmaker}: {e}")
            return None


def preload_all():
    """Pré-charge les données des deux bookmakers en parallèle"""
    print("🚀 Pré-chargement des données en cours...")
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(scrape_bookmaker, 'pmu'): 'pmu',
            executor.submit(scrape_bookmaker, 'winamax'): 'winamax'
        }
        for future in as_completed(futures):
            bm = futures[future]
            try:
                result = future.result()
                if result:
                    print(f"✅ {bm.upper()} pré-chargé ({result['count_3p']} matchs 3P, {result['count_2p']} matchs 2P)")
            except Exception as e:
                print(f"❌ Erreur pré-chargement {bm}: {e}")
    print("🎉 Pré-chargement terminé !")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/scrape/<bookmaker>')
def api_scrape(bookmaker):
    """Scrape et retourne matchs"""
    cache_key = f"{bookmaker}_all"
    cached = get_cached_data(cache_key)
    if cached:
        cached['from_cache'] = True
        return jsonify(cached)
    
    if bookmaker not in ['pmu', 'winamax']:
        return jsonify({'error': 'Bookmaker inconnu'}), 400
    
    result = scrape_bookmaker(bookmaker)
    if result:
        return jsonify(result)
    return jsonify({'error': 'Erreur de scraping', 'matches_3p': [], 'matches_2p': [], 'count_3p': 0, 'count_2p': 0}), 500


@app.route('/api/scrape-all')
def api_scrape_all():
    """Scrape les deux bookmakers en parallèle"""
    results = {}
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {
            executor.submit(lambda: get_cached_data('pmu_all') or scrape_bookmaker('pmu')): 'pmu',
            executor.submit(lambda: get_cached_data('winamax_all') or scrape_bookmaker('winamax')): 'winamax'
        }
        for future in as_completed(futures):
            bm = futures[future]
            try:
                results[bm] = future.result()
            except Exception as e:
                results[bm] = {'error': str(e)}
    
    return jsonify(results)


@app.route('/api/status')
def api_status():
    """Retourne le statut du cache et du pré-chargement"""
    current_time = time.time()
    status = {'preload': _preload_status.copy(), 'cache': {}}
    
    for bm in ['pmu', 'winamax']:
        key = f"{bm}_all"
        if key in _cache:
            cached = _cache[key]
            age = current_time - cached['timestamp']
            status['cache'][bm] = {
                'has_data': True,
                'count_3p': cached['data'].get('count_3p', 0),
                'count_2p': cached['data'].get('count_2p', 0),
                'age_seconds': round(age, 0),
                'expires_in': max(0, round(CACHE_DURATION - age, 0))
            }
        else:
            status['cache'][bm] = {'has_data': False}
    
    return jsonify(status)


@app.route('/api/clear-cache')
def api_clear_cache():
    global _cache
    _cache = {}
    return jsonify({'status': 'ok'})


# Pré-chargement au démarrage (dans un thread séparé)
def start_preload():
    time.sleep(2)  # Attendre que le serveur soit prêt
    preload_all()


if __name__ == '__main__':
    # Lancer le pré-chargement en background
    preload_thread = threading.Thread(target=start_preload, daemon=True)
    preload_thread.start()
    
    app.run(debug=True, port=5000, use_reloader=False)
