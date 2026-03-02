#!/usr/bin/env bash
# Build script for Render deployment
# https://docs.render.com/deploy-django

set -o errexit  # Exit on error

echo "Installing production dependencies..."
pip install -r requirements/production.txt

echo "Compiling Sass stylesheets..."
if command -v sass &> /dev/null; then
    sass assets/scss/styles.scss assets/css/styles.css --style=compressed --no-source-map
else
    echo "Warning: Sass not found, skipping CSS compilation"
fi

echo "Loading SVG icons..."
if [ -f scripts/load_icons.sh ]; then
    bash scripts/load_icons.sh
fi

echo "Collecting static files..."
python manage.py collectstatic --no-input -i scss -i icons

echo "Running database migrations..."
python manage.py migrate

echo "Setting up default user groups..."
python manage.py setup_default_groups || true

echo "Publishing sessions index pages..."
python manage.py publish_sessions_index || true

echo "Build complete!"
