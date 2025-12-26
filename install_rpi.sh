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
sudo apt-get install -y python3-venv python3-pip chromium-chromedriver chromium-browser git

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

# 4. Création du Service Systemd (Démarrage auto)
echo "⚙️ Création du service systemd..."
SERVICE_FILE="/etc/systemd/system/paris-sportifs.service"

sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=Paris Sportifs Optimizer Service
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

# 5. Activation du service
echo "🚀 Activation du service..."
sudo systemctl daemon-reload
sudo systemctl enable paris-sportifs.service
sudo systemctl start paris-sportifs.service

# 6. Installation Cloudflare Tunnel (Accès Web Gratuit)
echo "☁️ Installation de Cloudflare Tunnel..."
# Détection architecture pour binaire cloudflared
ARCH=$(dpkg --print-architecture)
if [ "$ARCH" = "armhf" ] || [ "$ARCH" = "armv7l" ]; then
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm -O cloudflared
elif [ "$ARCH" = "arm64" ]; then
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -O cloudflared
else
    wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cloudflared
fi

chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/

echo "✅ INSTALLATION TERMINÉE !"
echo "---------------------------------------------------"
echo "1. L'application tourne en fond (service 'paris-sportifs')"
echo "2. URL Locale : http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "🌍 POUR AVOIR UNE ADRESSE WEB GRATUITE :"
echo "   Lance cette commande pour créer un tunnel temporaire :"
echo "   cloudflared tunnel --url http://localhost:5000"
echo "---------------------------------------------------"
