# ⚽ BetOptimizer - 3 Joueurs × 100€ Freebets

Application qui trouve automatiquement les meilleurs matchs pour convertir vos freebets en profit garanti.

## 🎯 La Stratégie

**Vous êtes 3 joueurs avec chacun 100€ de freebet.**

Chaque joueur place son freebet sur une issue différente du même match :
- Joueur 1 → Victoire domicile (1)
- Joueur 2 → Match nul (N)  
- Joueur 3 → Victoire extérieur (2)

**Résultat : Quel que soit le résultat du match, un des freebets gagne !**

Le **profit garanti** = (cote minimale - 1) × 100€

## 📊 Exemple

Match **Lille vs Lens** (cotes 2.55 / 3.25 / 2.85) :

| Joueur | Pari | Cote | Gain si gagne |
|--------|------|------|---------------|
| Joueur 1 | Match Nul | 3.25 | +225€ |
| Joueur 2 | Victoire Lens | 2.85 | +185€ |
| Joueur 3 | Victoire Lille | 2.55 | **+155€** |

**💰 Profit garanti : +155€** (51.7% de conversion)

## 🚀 Installation & Lancement

```bash
cd /home/antoine/Desktop/ens/liste/paris_sportifs
source venv/bin/activate
python app.py
```

Ouvrir **http://localhost:5000**

## 📱 Fonctionnalités

1. **Liste des meilleurs matchs** - Classés par profit garanti décroissant
2. **Calculateur** - Pour vérifier manuellement des cotes
3. **Clic sur un match** - Affiche la répartition détaillée

## 🔑 Pour avoir les vraies cotes en temps réel

Par défaut, l'app utilise des données de démonstration. Pour avoir les vraies cotes :

### Option 1 : API gratuite (recommandé)

1. Créez un compte gratuit sur **https://the-odds-api.com/**
2. Récupérez votre clé API (500 requêtes gratuites/mois)
3. Lancez l'app avec la clé :

```bash
export ODDS_API_KEY='votre_clé_ici'
python app.py
```

### Option 2 : Ligne de commande

```bash
source venv/bin/activate
export ODDS_API_KEY='votre_clé'
python betclic_scraper.py
```

Affiche les matchs directement dans le terminal.

## 💡 Comment trouver le meilleur match ?

Cherchez des matchs avec **3 cotes proches et élevées** :

| Cotes | Cote min | Profit garanti | Conversion |
|-------|----------|----------------|------------|
| 2.55 / 3.25 / 2.85 | 2.55 | **+155€** | 51.7% |
| 2.30 / 3.40 / 3.10 | 2.30 | +130€ | 43.3% |
| 1.45 / 4.50 / 6.50 | 1.45 | +45€ | 15.0% |

**Plus la cote minimale est haute, plus le profit est important !**

Les derbys et matchs équilibrés ont souvent les meilleures cotes.

## 📁 Fichiers

```
paris_sportifs/
├── app.py              # Serveur web Flask
├── betclic_scraper.py  # Récupération et classement des matchs
├── calculator.py       # Moteur de calcul
├── templates/
│   └── index.html      # Interface web
├── requirements.txt    # Dépendances
└── venv/              # Environnement Python
```

## ⚠️ Avertissement

- Les freebets Betclic ne retournent généralement pas la mise
- Vérifiez toujours les conditions de vos freebets
- Les cotes peuvent changer rapidement
