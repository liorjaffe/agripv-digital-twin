#!/usr/bin/env sh
set -eu

rm -rf public-site
mkdir -p public-site/icons
cp agripv_dashboard.html public-site/index.html
cp public/manifest.webmanifest public/service-worker.js public-site/
cp public/icons/icon.svg public-site/icons/
cp public/_headers public-site/