"""WSGI config for the Quant web backend."""
from __future__ import annotations

import os
from pathlib import Path

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in os.sys.path:
    os.sys.path.insert(0, str(REPO_ROOT))

application = get_wsgi_application()
