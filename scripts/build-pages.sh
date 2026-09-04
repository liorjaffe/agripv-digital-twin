#!/usr/bin/env sh
set -eu

rm -rf public-site
mkdir -p public-site/icons public-site/data
cp agripv_dashboard.html public-site/index.html
sed -i.bak 's|public/data/period-results-2026.js|data/period-results-2026.js|g' public-site/index.html
rm public-site/index.html.bak
cp public/manifest.webmanifest public/service-worker.js public-site/
cp public/icons/icon.svg public-site/icons/
cp public/data/period-results-2026.js public-site/data/
cp public/_headers public-site/