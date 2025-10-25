from __future__ import annotations

import os
import time

from modules import timer
from modules import initialize_util
from modules import initialize

startup_timer = timer.startup_timer
startup_timer.record("launcher")

# Force proxy mode - no local SD models
os.environ.setdefault('SD_API_URL', 'http://localhost:7860')

initialize.imports()

initialize.check_versions()


def create_api(app):
    from modules.api.api import Api
    from modules.call_queue import queue_lock

    api = Api(app, queue_lock)
    return api


def api_only():
    from fastapi import FastAPI
    from modules.shared_cmd_options import cmd_opts

    # Skip model initialization for remote API proxy
    print("Skipping model initialization for remote API proxy...")
    
    app = FastAPI()
    initialize_util.setup_middleware(app)
    api = create_api(app)

    print(f"Startup time: {startup_timer.summary()}.")
    api.launch(
        server_name=initialize_util.gradio_server_name(),
        port=cmd_opts.port if cmd_opts.port else 7861,
        root_path=f"/{cmd_opts.subpath}" if cmd_opts.subpath else ""
    )


def webui():
    from modules.shared_cmd_options import cmd_opts

    # Force API mode for remote proxy
    cmd_opts.api = True
    cmd_opts.nowebui = True
    
    # Skip UI initialization for remote API proxy
    print("Starting Stable Diffusion WebUI Remote API Proxy...")
    print(f"Remote API URL: {os.getenv('SD_API_URL', 'Not set - using default http://localhost:7860')}")
    
    # Use API-only mode
    api_only()


if __name__ == "__main__":
    from modules.shared_cmd_options import cmd_opts

    if cmd_opts.nowebui:
        api_only()
    else:
        webui()
