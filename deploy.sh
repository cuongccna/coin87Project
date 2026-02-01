#!/bin/bash
set -e

# ==========================================
# Coin87 Deployment Script for Ubuntu VPS
# ==========================================

APP_DIR="/opt/coin87Project"
BACKEND_PORT=9000
FRONTEND_PORT=9001
USER=$(whoami)
 
# Load .env early if present to pick up DB credentials and other config
if [ -f ".env" ]; then
    # Export variables defined in .env into environment for this script
    set -o allexport
    # shellcheck disable=SC1090
    source .env
    set +o allexport
fi
echo ">>> Starting deployment for Coin87..."
echo ">>> Target Directory: $APP_DIR"
echo ">>> User: $USER"

# Check if running in the correct directory
if [ "$PWD" != "$APP_DIR" ]; then
    echo "WARNING: You are running this script from $PWD, but target is $APP_DIR."
    echo "Please clone the repository directly into $APP_DIR or move it there."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 1. System Updates & Dependencies
echo ">>> Installing specific system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip python3-dev build-essential nodejs npm postgresql postgresql-contrib postgresql-client

# 1.5 Database Setup (Fix Permissions)
echo ">>> Ensuring Database & User permissions..."
DB_NAME="coin87_db"
DB_USER="coin87_user"
# DB_PASS is intentionally NOT hardcoded. Prefer value from environment/.env.
# If not present, prompt the operator securely.
if [ -z "${DB_PASS:-}" ]; then
    # Prompt for password without echo
    read -r -s -p "Enter database password for $DB_USER (will not echo): " DB_PASS
    echo
fi

if sudo -u postgres psql -c "SELECT 1;" &> /dev/null; then
    # Create User
    sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname = '$DB_USER'" | grep -q 1 || \
        sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
    
    # Create Database
    sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
        sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

    # Grant Privileges
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
    # Critical fix for Schema Public access
    sudo -u postgres psql -d $DB_NAME -c "GRANT ALL ON SCHEMA public TO $DB_USER;"
    
    echo "Database permissions verified."
else
    echo "WARNING: Could not connect to Postgres as sudo. setup skipped."
fi


# 2. Verify Node.js version (PM2 needs Node)
echo ">>> Checking Node.js..."
node -v
npm -v

# 2.5 Setup Nginx
echo ">>> Setting up Nginx..."
if ! command -v nginx &> /dev/null; then
    echo "Installing Nginx..."
    sudo apt-get install -y nginx
fi

# Copy Nginx Config
if [ -f "config/nginx/cbottrading.cloud.conf" ]; then
    echo "Configuring Nginx for cbottrading.cloud..."
    sudo cp config/nginx/cbottrading.cloud.conf /etc/nginx/sites-available/cbottrading.cloud
    
    # Symlink if not exists
    if [ ! -f "/etc/nginx/sites-enabled/cbottrading.cloud" ]; then
        sudo ln -s /etc/nginx/sites-available/cbottrading.cloud /etc/nginx/sites-enabled/
    fi
    
    # Ensure webroot for Certbot exists
    if [ ! -d "/var/www/html" ]; then
        echo "Creating /var/www/html for Certbot..."
        sudo mkdir -p /var/www/html
        sudo chown -R $USER:$USER /var/www/html
        sudo chmod -R 755 /var/www/html
    fi
    
    # Test and Reload
    sudo nginx -t && sudo systemctl reload nginx
    echo "Nginx configured successfully."
else
    echo "WARNING: Nginx config file not found!"
fi

# 3. Setup Backend
echo ">>> Setting up Backend..."
cd backend

# Create .env if missing (Critical for Alembic)
if [ ! -f ".env" ]; then
    echo "Creating backend .env..."
    # Write values from the variables (DB_PASS provided above). Avoid echoing DB_PASS to stdout.
    printf "%s\n" "DATABASE_URL=postgresql+psycopg2://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME" > .env
    printf "%s\n" "C87_MARKET_INTEL_URL=http://localhost:8000/v1/market/intel" >> .env
    printf "%s\n" "C87_JWT_SECRET=coin87-prod-secret-change-me" >> .env
    echo "Environment file created (sensitive values written)."
fi

# Create Virtual Environment
if [ ! -d "venv" ]; then
    echo "Creating python virtual environment..."
    python3 -m venv venv
fi

# Activate & Install Deps
source venv/bin/activate
echo "Installing Python requirements..."
pip install --upgrade pip
pip install -r requirements.txt

# Database Migrations
if [ -f "alembic.ini" ]; then
    echo "Running Database Migrations..."
    # Ensure env vars are present. If .env exists, export them? 
    # Usually alembic/env.py loads .env using python-dotenv.
    # Exporting just in case env.py doesn't load it automatically when run from here
    export $(cat .env | xargs)
    alembic upgrade head
else
    echo "WARNING: alembic.ini not found, skipping migrations."
fi

# Ensure sources.yaml is in the right place
if [ -f "ingestion/config/sources.yaml" ]; then
    echo "Sources configuration authenticated."
    # If we need to symlink or copy, do it here. Currently script uses direct path or env var.
    # Ensuring C87_SOURCES_YAML env var is set in PM2 config is handled in ecosystem.config.js
else
    echo "WARNING: sources.yaml not found at backend/ingestion/config/sources.yaml"
fi

# Ensure Proxy config exists in .env
if ! grep -q "C87_PROXY_URL" .env; then
    echo "WARNING: C87_PROXY_URL not found in .env. Appending empty placeholder."
    echo "" >> .env
    echo "# Proxy Configuration" >> .env
    echo "C87_PROXY_URL=" >> .env
fi

deactivate
cd ..

# 4. Setup Frontend
echo ">>> Setting up Frontend..."
cd frontend

if [ ! -f ".env.local" ]; then
    echo "Creating default .env.local..."
    # Configured for cbottrading.cloud
    echo "NEXT_PUBLIC_API_URL=http://cbottrading.cloud" > .env.local
    echo "WARNING: Created .env.local pointing to http://cbottrading.cloud"
fi

echo "Installing Frontend Dependencies..."
npm install

echo "Building Frontend..."
npm run build

cd ..

# 5. PM2 Process Management
echo ">>> Configuring PM2..."
# Install PM2 globally if not exists
if ! command -v pm2 &> /dev/null; then
    sudo npm install -g pm2
fi

# Start/Restart Ecosystem
pm2 start ecosystem.config.js

# Save list
pm2 save

# Setup startup hook (needs sudo usually, but pm2 startup generates command)
echo "To enable PM2 startup on boot, run the command displayed by: 'pm2 startup'"

# 6. Cron Jobs Setup
echo ">>> Setting up Cron Jobs..."
chmod +x backend/scripts/*.sh

CRON_FILE="my_cron_temp"

# Dump current cron
crontab -l > "$CRON_FILE" 2>/dev/null || touch "$CRON_FILE"

# Function to ensure job exists
add_cron_if_missing() {
    local cmd="$2"
    local schedule="$1"
    if ! grep -Fq "$cmd" "$CRON_FILE"; then
        echo "Adding cron: $cmd"
        echo "$schedule $cmd >> $APP_DIR/cron.log 2>&1" >> "$CRON_FILE"
    else
        echo "Cron already exists: $cmd"
    fi
}

# Run Ingestion every 5 minutes (Smart Rate Control handles actual execution)
add_cron_if_missing "*/5 * * * *" "$APP_DIR/backend/scripts/run_ingestion.sh"

# Run Derive Task every 10 minutes
add_cron_if_missing "*/10 * * * *" "$APP_DIR/backend/scripts/run_derive_risk.sh"

# Run Feed Promotion every 5 minutes (New Inversion Feed Flow)
add_cron_if_missing "*/3 * * * *" "$APP_DIR/backend/scripts/run_promote_feed.sh"

# Run Snapshot every hour
add_cron_if_missing "0 * * * *" "$APP_DIR/backend/scripts/run_snapshot_env.sh"

# Run Housekeeping daily at midnight
add_cron_if_missing "0 0 * * *" "$APP_DIR/backend/scripts/run_housekeeping.sh"

# Install new cron file
crontab "$CRON_FILE"
rm "$CRON_FILE"

echo "=========================================="
echo "Deployment Finished Successfully!"
echo "Backend running on port: $BACKEND_PORT"
echo "Frontend running on port: $FRONTEND_PORT"
echo "Check status with: pm2 status"
echo "Logs available at: ~/.pm2/logs and $APP_DIR/cron.log"
echo "=========================================="
