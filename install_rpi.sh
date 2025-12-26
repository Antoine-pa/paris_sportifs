#!/bin/bash

# ==========================================
# PARIS SPORTIFS OPTIMIZER - INSTALLATEUR RPI
# ==========================================

echo "🍓 Installation Paris Sportifs Optimizer sur Raspberry Pi..."
USER_HOME=$(eval echo ~$SUDO_USER)
PROJECT_DIR=$(pwd)

# 1. Mise à jour système et dépendances
echo "📦 Installation des paquets système..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip chromium-chromedriver chromium-browser git unzip

# 2. Création Virtualenv
if [ ! -d "venv" ]; then
    echo "🐍 Création de l'environnement virtuel Python..."
    python3 -m venv venv
fi

# 3. Installation des libs Python
echo "📚 Installation des librairies Python..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Création du Service App (Flask)
echo "⚙️ Création du service Application..."
SERVICE_FILE="/etc/systemd/system/paris-sportifs.service"

sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=Paris Sportifs App
After=network.target

[Service]
User=$SUDO_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python app.py
Restart=always
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOL

sudo systemctl daemon-reload
sudo systemctl enable paris-sportifs.service
sudo systemctl start paris-sportifs.service

# 5. Installation Ngrok (Pour URL Fixe)
echo "🌍 Installation de Ngrok (URL Statique)..."
if [ ! -f "/usr/local/bin/ngrok" ]; then
    wget -q https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-arm.tgz
    sudo tar xvzf ngrok-v3-stable-linux-arm.tgz -C /usr/local/bin
    rm ngrok-v3-stable-linux-arm.tgz
fi

echo ""
echo "======================================================="
echo "🔴 CONFIGURATION NGROK REQUISE (POUR URL FIXE) 🔴"
echo "-------------------------------------------------------"
echo "1. Crée un compte gratuit sur https://dashboard.ngrok.com"
echo "2. Va dans 'Cloud Edge' > 'Domains' et crée un domaine (ex: mon-site.ngrok-free.app)"
echo "3. Copie ton Authtoken depuis le dashboard."
echo "======================================================="
echo ""
read -p "Colle ton NGROK_AUTHTOKEN ici : " NGROK_TOKEN
read -p "Colle ton DOMAINE FIXE (ex: mon-site.ngrok-free.app) : " NGROK_DOMAIN

if [ ! -z "$NGROK_TOKEN" ] && [ ! -z "$NGROK_DOMAIN" ]; then
    # Configurer Ngrok
    ngrok config add-authtoken $NGROK_TOKEN
    
    # Créer le service Ngrok
    NGROK_SERVICE="/etc/systemd/system/ngrok-tunnel.service"
    sudo bash -c "cat > $NGROK_SERVICE" <<EOL
[Unit]
Description=Ngrok Tunnel
After=network.target

[Service]
ExecStart=/usr/local/bin/ngrok http --domain=$NGROK_DOMAIN 5000
Restart=always
User=$SUDO_USER

[Install]
WantedBy=multi-user.target
EOL

    sudo systemctl enable ngrok-tunnel.service
    sudo systemctl start ngrok-tunnel.service
    
    echo "✅ TOUT EST CONFIGURÉ !"
    echo "🌐 Ton site est accessible 24/7 sur : https://$NGROK_DOMAIN"
else
    echo "⚠️ Configuration Ngrok ignorée (infos manquantes)."
    echo "Tu devras lancer le tunnel manuellement."
fi
