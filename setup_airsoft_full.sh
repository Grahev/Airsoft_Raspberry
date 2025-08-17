#!/bin/bash
set -e

APP_DIR="$HOME/airsoft_app"
REPO_URL="https://github.com/Grahev/Airsoft_Raspberry.git"

echo "Starting Airsoft setup..."

# Detect if running in Docker
if [ -f /.dockerenv ]; then
    IN_DOCKER=true
    echo "Running inside Docker, systemd commands will be skipped."
else
    IN_DOCKER=false
fi

# 1. Create app directory
mkdir -p "$APP_DIR"
cd "$APP_DIR"

# 2. Clone repo if not exists
if [ ! -d "$APP_DIR/.git" ]; then
    echo "Cloning repository..."
    git clone "$REPO_URL" .
else
    echo "Repository already exists, pulling latest changes..."
    git pull
fi

# 3. Create Python virtual environment
if [ ! -d "$APP_DIR/venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# 4. Activate venv and install dependencies
echo "Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

# 5. Setup systemd service (skip in Docker)
SERVICE_FILE="/etc/systemd/system/airsoft.service"
if [ "$IN_DOCKER" = false ]; then
    echo "Creating systemd service..."
    sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Airsoft Server
After=network.target

[Service]
User=$USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

    echo "Enabling and starting service..."
    sudo systemctl daemon-reload
    sudo systemctl enable airsoft.service
    sudo systemctl start airsoft.service
else
    echo "Docker environment detected, skipping systemd setup."
fi

echo "Setup complete!"
if [ "$IN_DOCKER" = false ]; then
    echo "Airsoft server is running and will auto-start on boot."
else
    echo "You can start the server manually inside Docker:"
    echo "source venv/bin/activate && uvicorn app:app --host 0.0.0.0 --port 8000"
fi
