import importlib
import logging
import os
import sys
import warnings
from threading import Thread

from modules.timer import startup_timer


def imports():
    # Skip torch imports in proxy mode
    logging.getLogger("xformers").addFilter(lambda record: 'A matching Triton is not available' not in record.getMessage())
    
    startup_timer.record("import torch")
    warnings.filterwarnings(action="ignore", category=DeprecationWarning, module="pytorch_lightning")
    warnings.filterwarnings(action="ignore", category=UserWarning, module="torchvision")

    os.environ.setdefault('GRADIO_ANALYTICS_ENABLED', 'False')
    import gradio  # noqa: F401
    startup_timer.record("import gradio")

    from modules import paths, timer, import_hook, errors  # noqa: F401
    startup_timer.record("setup paths")

    # Skip ldm and sgm imports in proxy mode
    if not os.getenv('SD_API_URL'):
        import ldm.modules.encoders.modules  # noqa: F401
        startup_timer.record("import ldm")

        import sgm.modules.encoders.modules  # noqa: F401
        startup_timer.record("import sgm")
    else:
        print("Skipping ldm and sgm imports in proxy mode")
        startup_timer.record("import ldm")
        startup_timer.record("import sgm")

    from modules import shared_init
    shared_init.initialize()
    startup_timer.record("initialize shared")

    from modules import processing, gradio_extensons, ui  # noqa: F401
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

    # Always run in proxy mode - no local model loading
    print("Running in API proxy mode, skipping all local model loading")
    print(f"SD_API_URL: {os.getenv('SD_API_URL', 'Not set')}")

    initialize_rest(reload_script_modules=False)


def initialize_rest(*, reload_script_modules=False):
    """
    Called both from initialize() and when reloading the webui.
    """
    from modules.shared_cmd_options import cmd_opts

    from modules import sd_samplers
    sd_samplers.set_samplers()
    startup_timer.record("set samplers")

    from modules import extensions
    extensions.list_extensions()
    startup_timer.record("list extensions")

    from modules import initialize_util
    initialize_util.restore_config_state_file()
    startup_timer.record("restore config state file")

    from modules import shared, upscaler, scripts
    if cmd_opts.ui_debug_mode:
        shared.sd_upscalers = upscaler.UpscalerLanczos().scalers
        scripts.load_scripts()
        return

    # Skip all local model loading in proxy mode
    print("Skipping local model loading in proxy mode")

    from modules import localization
    localization.list_localizations(cmd_opts.localizations_dir)
    startup_timer.record("list localizations")

    with startup_timer.subcategory("load scripts"):
        scripts.load_scripts()

    if reload_script_modules and shared.opts.enable_reloading_ui_scripts:
        for module in [module for name, module in sys.modules.items() if name.startswith("modules.ui")]:
            importlib.reload(module)
        startup_timer.record("reload script modules")

    # Skip model-related initialization in proxy mode
    print("Skipping model-related initialization in proxy mode")
