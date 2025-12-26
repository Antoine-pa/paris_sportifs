#!/bin/bash

# Script d'installation automatique pour Raspberry Pi
echo "🍓 Installation Paris Sportifs Optimizer sur Raspberry Pi..."

# 1. Mise à jour système et dépendances
echo "📦 Installation des paquets système..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip chromium-chromedriver chromium-browser git

# 2. Création Virtualenv
if [ ! -d "venv" ]; then
    echo "🐍 Création de l'environnement virtuel Python..."
    python3 -m venv venv
fi

# 3. Activation et Installation requirements
echo "📚 Installation des librairies Python..."
source venv/bin/activate
pip install --upgrade pip
# Selenium sur ARM/RPi peut être capricieux, on force certaines versions si besoin
pip install -r requirements.txt

# 4. Configuration du Cron (Scraping toutes les heures)
CURRENT_PATH=$(pwd)
CRON_CMD="0 * * * * cd $CURRENT_PATH && $CURRENT_PATH/venv/bin/python build_static.py >> scraper.log 2>&1 && git add . && git commit -m 'Auto update' && git push"

# Vérifier si le cron existe déjà
(crontab -l 2>/dev/null | grep -F "build_static.py") || (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -

echo "✅ Installation terminée !"
echo "🕒 Le scraper tournera automatiquement toutes les heures."
echo "ℹ️ Pour lancer un scraping manuel : source venv/bin/activate && python build_static.py"
