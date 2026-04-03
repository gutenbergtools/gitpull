#!/usr/bin/env bash
cd /home/htdocs/dopull
set -o allexport; source ./.env; set +o allexport
exec python3 dopull.py
