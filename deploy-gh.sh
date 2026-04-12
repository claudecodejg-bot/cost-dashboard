#!/bin/bash
set -e

echo "🔄 Generating dashboard from session logs..."
python3 generate-dashboard.py --output dist/index.html

echo "📦 Committing to git..."
git add dist/
git commit -m "Update dashboard $(date +%Y-%m-%d)" || echo "No changes to commit"

echo "🚀 Pushing to GitHub Pages..."
git push origin main

echo "✅ Deployed! URL will be https://[YOUR-GITHUB-USERNAME].github.io/cost-dashboard/"
