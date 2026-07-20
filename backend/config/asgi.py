"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django_asgi_app = get_asgi_application()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from chat.fastapi_stream import app as fastapi_app

application = FastAPI(title="DocuMind AI Application")

# Configure CORS
application.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount FastAPI stream app at /api/chat/fastapi
application.mount("/api/chat/fastapi", fastapi_app)

# Mount Django app for everything else
application.mount("/", django_asgi_app)
