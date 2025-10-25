import importlib
import logging
import os
import sys
import warnings
from threading import Thread

from modules.timer import startup_timer


def imports():
    # Skip ML imports for remote API proxy
    print("Skipping ML imports for remote API proxy...")
    
    os.environ.setdefault('GRADIO_ANALYTICS_ENABLED', 'False')
    import gradio  # noqa: F401
    startup_timer.record("import gradio")

    from modules import paths, timer, import_hook, errors  # noqa: F401
    startup_timer.record("setup paths")

    from modules import shared_init
    shared_init.initialize()
    startup_timer.record("initialize shared")

    from modules import gradio_extensons  # noqa: F401
    startup_timer.record("other imports")


def check_versions():
    from modules.shared_cmd_options import cmd_opts

    if not cmd_opts.skip_version_check:
        from modules import errors
        errors.check_versions()


def initialize():
    from modules import initialize_util
    initialize_util.fix_torch_version()
    initialize_util.fix_pytorch_lightning()
    initialize_util.fix_asyncio_event_loop_policy()
    initialize_util.validate_tls_options()
    initialize_util.configure_sigint_handler()
    initialize_util.configure_opts_onchange()

    # Skip all model loading for remote API proxy
    print("Running in remote API proxy mode, skipping all local model loading")
    print(f"SD_API_URL: {os.getenv('SD_API_URL', 'Not set')}")

    initialize_rest(reload_script_modules=False)


def initialize_rest(*, reload_script_modules=False):
    """
    Called both from initialize() and when reloading the webui.
    """
    from modules.shared_cmd_options import cmd_opts

    from modules import extensions
    extensions.list_extensions()
    startup_timer.record("list extensions")

    from modules import initialize_util
    initialize_util.restore_config_state_file()
    startup_timer.record("restore config state file")

    from modules import shared
    if cmd_opts.ui_debug_mode:
        # Skip upscaler and scripts for remote API proxy
        return

    from modules import localization
    localization.list_localizations(cmd_opts.localizations_dir)
    startup_timer.record("list localizations")

    # Skip all model-related initialization for remote API proxy
    print("Skipping all model-related initialization for remote API proxy...")
