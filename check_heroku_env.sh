#!/bin/bash
# Script to check Heroku environment configuration

echo "=== Checking Heroku Configuration ==="
echo ""

echo "1. Checking if logged into Heroku..."
heroku auth:whoami

echo ""
echo "2. Current Heroku config vars:"
heroku config

echo ""
echo "3. Checking required environment variables..."
REQUIRED_VARS=("SECRET_KEY" "ALLOWED_HOSTS" "DATABASE_URL")

for var in "${REQUIRED_VARS[@]}"; do
    if heroku config:get "$var" > /dev/null 2>&1; then
        value=$(heroku config:get "$var")
        if [ -z "$value" ]; then
            echo "❌ $var is NOT set"
        else
            echo "✅ $var is set"
        fi
    else
        echo "❌ $var is NOT set"
    fi
done

echo ""
echo "4. Checking recent logs for errors..."
heroku logs --tail --num 50

echo ""
echo "=== Configuration Check Complete ==="
