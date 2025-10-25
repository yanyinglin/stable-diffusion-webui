import base64
import io
import os
import time
import datetime
import uvicorn
import ipaddress
import requests
import gradio as gr
from threading import Lock
from io import BytesIO
from fastapi import APIRouter, Depends, FastAPI, Request, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from secrets import compare_digest

import modules.shared as shared
from modules import images, errors, restart, script_callbacks, infotext_utils
from modules.api import models
from modules.shared import opts
from PIL import PngImagePlugin
from typing import Any
import piexif
import piexif.helper

# Local processing functions removed for remote API proxy


def verify_url(url):
    """Returns True if the url refers to a global resource."""

    import socket
    from urllib.parse import urlparse
    try:
        parsed_url = urlparse(url)
        domain_name = parsed_url.netloc
        host = socket.gethostbyname_ex(domain_name)
        for ip in host[2]:
            ip_addr = ipaddress.ip_address(ip)
            if not ip_addr.is_global:
                return False
    except Exception:
        return False

    return True


def decode_base64_to_image(encoding):
    if encoding.startswith("http://") or encoding.startswith("https://"):
        if not opts.api_enable_requests:
            raise HTTPException(status_code=500, detail="Requests not allowed")

        if opts.api_forbid_local_requests and not verify_url(encoding):
            raise HTTPException(status_code=500, detail="Request to local resource not allowed")

        headers = {'user-agent': opts.api_useragent} if opts.api_useragent else {}
        response = requests.get(encoding, timeout=30, headers=headers)
        try:
            image = images.read(BytesIO(response.content))
            return image
        except Exception as e:
            raise HTTPException(status_code=500, detail="Invalid image url") from e

    if encoding.startswith("data:image/"):
        encoding = encoding.split(";")[1].split(",")[1]
    try:
        image = images.read(BytesIO(base64.b64decode(encoding)))
        return image
    except Exception as e:
        raise HTTPException(status_code=500, detail="Invalid encoded image") from e


def encode_pil_to_base64(image):
    with io.BytesIO() as output_bytes:
        if isinstance(image, str):
            return image
        if opts.samples_format.lower() == 'png':
            use_metadata = False
            metadata = PngImagePlugin.PngInfo()
            for key, value in image.info.items():
                if isinstance(key, str) and isinstance(value, str):
                    metadata.add_text(key, value)
                    use_metadata = True
            image.save(output_bytes, format="PNG", pnginfo=(metadata if use_metadata else None), quality=opts.jpeg_quality)

        elif opts.samples_format.lower() in ("jpg", "jpeg", "webp"):
            if image.mode in ("RGBA", "P"):
                image = image.convert("RGB")
            parameters = image.info.get('parameters', None)
            exif_bytes = piexif.dump({
                "Exif": { piexif.ExifIFD.UserComment: piexif.helper.UserComment.dump(parameters or "", encoding="unicode") }
            })
            if opts.samples_format.lower() in ("jpg", "jpeg"):
                image.save(output_bytes, format="JPEG", exif = exif_bytes, quality=opts.jpeg_quality)
            else:
                image.save(output_bytes, format="WEBP", exif = exif_bytes, quality=opts.jpeg_quality)

        else:
            raise HTTPException(status_code=500, detail="Invalid image format")

        bytes_data = output_bytes.getvalue()

    return base64.b64encode(bytes_data)


def api_middleware(app: FastAPI):
    rich_available = False
    try:
        if os.environ.get('WEBUI_RICH_EXCEPTIONS', None) is not None:
            import anyio  # importing just so it can be placed on silent list
            import starlette  # importing just so it can be placed on silent list
            from rich.console import Console
            console = Console()
            rich_available = True
    except Exception:
        pass

    @app.middleware("http")
    async def log_and_time(req: Request, call_next):
        ts = time.time()
        res: Response = await call_next(req)
        duration = str(round(time.time() - ts, 4))
        res.headers["X-Process-Time"] = duration
        endpoint = req.scope.get('path', 'err')
        if shared.cmd_opts.api_log and endpoint.startswith('/sdapi'):
            print('API {t} {code} {prot}/{ver} {method} {endpoint} {cli} {duration}'.format(
                t=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                code=res.status_code,
                ver=req.scope.get('http_version', '0.0'),
                cli=req.scope.get('client', ('0:0.0.0', 0))[0],
                prot=req.scope.get('scheme', 'err'),
                method=req.scope.get('method', 'err'),
                endpoint=endpoint,
                duration=duration,
            ))
        return res

    def handle_exception(request: Request, e: Exception):
        err = {
            "error": type(e).__name__,
            "detail": vars(e).get('detail', ''),
            "body": vars(e).get('body', ''),
            "errors": str(e),
        }
        if not isinstance(e, HTTPException):  # do not print backtrace on known httpexceptions
            message = f"API error: {request.method}: {request.url} {err}"
            if rich_available:
                print(message)
                console.print_exception(show_locals=True, max_frames=2, extra_lines=1, suppress=[anyio, starlette], word_wrap=False, width=min([console.width, 200]))
            else:
                errors.report(message, exc_info=True)
        return JSONResponse(status_code=vars(e).get('status_code', 500), content=jsonable_encoder(err))

    @app.middleware("http")
    async def exception_handling(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            return handle_exception(request, e)

    @app.exception_handler(Exception)
    async def fastapi_exception_handler(request: Request, e: Exception):
        return handle_exception(request, e)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, e: HTTPException):
        return handle_exception(request, e)


class Api:
    def __init__(self, app: FastAPI, queue_lock: Lock):
        if shared.cmd_opts.api_auth:
            self.credentials = {}
            for auth in shared.cmd_opts.api_auth.split(","):
                user, password = auth.split(":")
                self.credentials[user] = password

        self.router = APIRouter()
        self.app = app
        self.queue_lock = queue_lock
        api_middleware(self.app)
        self.add_api_route("/sdapi/v1/txt2img", self.text2imgapi, methods=["POST"], response_model=models.TextToImageResponse)
        self.add_api_route("/sdapi/v1/img2img", self.img2imgapi, methods=["POST"], response_model=models.ImageToImageResponse)
        self.add_api_route("/sdapi/v1/extra-single-image", self.extras_single_image_api, methods=["POST"], response_model=models.ExtrasSingleImageResponse)
        self.add_api_route("/sdapi/v1/extra-batch-images", self.extras_batch_images_api, methods=["POST"], response_model=models.ExtrasBatchImagesResponse)
        self.add_api_route("/sdapi/v1/png-info", self.pnginfoapi, methods=["POST"], response_model=models.PNGInfoResponse)
        self.add_api_route("/sdapi/v1/progress", self.progressapi, methods=["GET"], response_model=models.ProgressResponse)
        self.add_api_route("/sdapi/v1/interrogate", self.interrogateapi, methods=["POST"])
        self.add_api_route("/sdapi/v1/interrupt", self.interruptapi, methods=["POST"])
        self.add_api_route("/sdapi/v1/skip", self.skip, methods=["POST"])
        self.add_api_route("/sdapi/v1/options", self.get_config, methods=["GET"], response_model=models.OptionsModel)
        self.add_api_route("/sdapi/v1/options", self.set_config, methods=["POST"])
        self.add_api_route("/sdapi/v1/cmd-flags", self.get_cmd_flags, methods=["GET"], response_model=models.FlagsModel)
        self.add_api_route("/sdapi/v1/samplers", self.get_samplers, methods=["GET"], response_model=list[models.SamplerItem])
        self.add_api_route("/sdapi/v1/schedulers", self.get_schedulers, methods=["GET"], response_model=list[models.SchedulerItem])
        self.add_api_route("/sdapi/v1/upscalers", self.get_upscalers, methods=["GET"], response_model=list[models.UpscalerItem])
        self.add_api_route("/sdapi/v1/latent-upscale-modes", self.get_latent_upscale_modes, methods=["GET"], response_model=list[models.LatentUpscalerModeItem])
        self.add_api_route("/sdapi/v1/sd-models", self.get_sd_models, methods=["GET"], response_model=list[models.SDModelItem])
        self.add_api_route("/sdapi/v1/sd-vae", self.get_sd_vaes, methods=["GET"], response_model=list[models.SDVaeItem])
        self.add_api_route("/sdapi/v1/hypernetworks", self.get_hypernetworks, methods=["GET"], response_model=list[models.HypernetworkItem])
        self.add_api_route("/sdapi/v1/face-restorers", self.get_face_restorers, methods=["GET"], response_model=list[models.FaceRestorerItem])
        self.add_api_route("/sdapi/v1/realesrgan-models", self.get_realesrgan_models, methods=["GET"], response_model=list[models.RealesrganItem])
        self.add_api_route("/sdapi/v1/prompt-styles", self.get_prompt_styles, methods=["GET"], response_model=list[models.PromptStyleItem])
        self.add_api_route("/sdapi/v1/embeddings", self.get_embeddings, methods=["GET"], response_model=models.EmbeddingsResponse)
        self.add_api_route("/sdapi/v1/refresh-embeddings", self.refresh_embeddings, methods=["POST"])
        self.add_api_route("/sdapi/v1/refresh-checkpoints", self.refresh_checkpoints, methods=["POST"])
        self.add_api_route("/sdapi/v1/refresh-vae", self.refresh_vae, methods=["POST"])
        self.add_api_route("/sdapi/v1/create/embedding", self.create_embedding, methods=["POST"], response_model=models.CreateResponse)
        self.add_api_route("/sdapi/v1/create/hypernetwork", self.create_hypernetwork, methods=["POST"], response_model=models.CreateResponse)
        self.add_api_route("/sdapi/v1/train/embedding", self.train_embedding, methods=["POST"], response_model=models.TrainResponse)
        self.add_api_route("/sdapi/v1/train/hypernetwork", self.train_hypernetwork, methods=["POST"], response_model=models.TrainResponse)
        self.add_api_route("/sdapi/v1/memory", self.get_memory, methods=["GET"], response_model=models.MemoryResponse)
        self.add_api_route("/sdapi/v1/unload-checkpoint", self.unloadapi, methods=["POST"])
        self.add_api_route("/sdapi/v1/reload-checkpoint", self.reloadapi, methods=["POST"])
        self.add_api_route("/sdapi/v1/scripts", self.get_scripts_list, methods=["GET"], response_model=models.ScriptsList)
        self.add_api_route("/sdapi/v1/script-info", self.get_script_info, methods=["GET"], response_model=list[models.ScriptInfo])
        self.add_api_route("/sdapi/v1/extensions", self.get_extensions_list, methods=["GET"], response_model=list[models.ExtensionItem])

        if shared.cmd_opts.api_server_stop:
            self.add_api_route("/sdapi/v1/server-kill", self.kill_webui, methods=["POST"])
            self.add_api_route("/sdapi/v1/server-restart", self.restart_webui, methods=["POST"])
            self.add_api_route("/sdapi/v1/server-stop", self.stop_webui, methods=["POST"])

        # Script initialization removed for remote API proxy



    def add_api_route(self, path: str, endpoint, **kwargs):
        if shared.cmd_opts.api_auth:
            return self.app.add_api_route(path, endpoint, dependencies=[Depends(self.auth)], **kwargs)
        return self.app.add_api_route(path, endpoint, **kwargs)

    def auth(self, credentials: HTTPBasicCredentials = Depends(HTTPBasic())):
        if credentials.username in self.credentials:
            if compare_digest(credentials.password, self.credentials[credentials.username]):
                return True

        raise HTTPException(status_code=401, detail="Incorrect username or password", headers={"WWW-Authenticate": "Basic"})

    def get_scripts_list(self):
        # Return empty for remote API
        return models.ScriptsList(txt2img=[], img2img=[])

    def get_script_info(self):
        # Return empty for remote API
        return []

    def text2imgapi(self, txt2imgreq: models.StableDiffusionTxt2ImgProcessingAPI):
        # Use remote API
        from modules.api_proxy import RemoteSDAPIClient
        client = RemoteSDAPIClient()
        params = txt2imgreq.dict()
        return client.txt2img(params)

    def img2imgapi(self, img2imgreq: models.StableDiffusionImg2ImgProcessingAPI):
        # Use remote API
        from modules.api_proxy import RemoteSDAPIClient
        client = RemoteSDAPIClient()
        params = img2imgreq.dict()
        return client.img2img(params)

    def extras_single_image_api(self, req: models.ExtrasSingleImageRequest):
        # Use remote API
        from modules.api_proxy import RemoteSDAPIClient
        client = RemoteSDAPIClient()
        params = req.dict()
        return client.extras_single_image(params)

    def extras_batch_images_api(self, req: models.ExtrasBatchImagesRequest):
        # Use remote API
        from modules.api_proxy import RemoteSDAPIClient
        client = RemoteSDAPIClient()
        params = req.dict()
        return client.extras_batch_images(params)

    def pnginfoapi(self, req: models.PNGInfoRequest):
        # Use remote API
        from modules.api_proxy import RemoteSDAPIClient
        client = RemoteSDAPIClient()
        params = req.dict()
        return client.png_info(params)

    def progressapi(self, req: models.ProgressRequest = Depends()):
        # Use remote API
        from modules.api_proxy import RemoteSDAPIClient
        client = RemoteSDAPIClient()
        return client.get_progress()

    def interrogateapi(self, interrogatereq: models.InterrogateRequest):
        # Use remote API
        from modules.api_proxy import RemoteSDAPIClient
        client = RemoteSDAPIClient()
        params = interrogatereq.dict()
        return client.interrogate(params)

    def interruptapi(self):
        # Use remote API
        from modules.api_proxy import RemoteSDAPIClient
        client = RemoteSDAPIClient()
        return client.interrupt()

    def unloadapi(self):
        # Not applicable for remote API
        return {}

    def reloadapi(self):
        # Not applicable for remote API
        return {}

    def skip(self):
        # Use remote API
        from modules.api_proxy import RemoteSDAPIClient
        client = RemoteSDAPIClient()
        return client.skip()

    def get_config(self):
        options = {}
        for key in shared.opts.data.keys():
            metadata = shared.opts.data_labels.get(key)
            if(metadata is not None):
                options.update({key: shared.opts.data.get(key, shared.opts.data_labels.get(key).default)})
            else:
                options.update({key: shared.opts.data.get(key, None)})

        return options

    def set_config(self, req: dict[str, Any]):
        checkpoint_name = req.get("sd_model_checkpoint", None)
        if checkpoint_name is not None and checkpoint_name not in sd_models.checkpoint_aliases:
            raise RuntimeError(f"model {checkpoint_name!r} not found")

        for k, v in req.items():
            shared.opts.set(k, v, is_api=True)

        shared.opts.save(shared.config_filename)
        return

    def get_cmd_flags(self):
        return vars(shared.cmd_opts)

    def get_samplers(self):
        # Return empty list for remote API
        return []

    def get_schedulers(self):
        # Return empty list for remote API
        return []

    def get_upscalers(self):
        # Return empty list for remote API
        return []

    def get_latent_upscale_modes(self):
        # Return empty list for remote API
        return []

    def get_sd_models(self):
        # Return empty list for remote API
        return []

    def get_sd_vaes(self):
        # Return empty list for remote API
        return []

    def get_hypernetworks(self):
        # Return empty list for remote API
        return []

    def get_face_restorers(self):
        # Return empty list for remote API
        return []

    def get_realesrgan_models(self):
        # Return empty list for remote API
        return []

    def get_prompt_styles(self):
        styleList = []
        for k in shared.prompt_styles.styles:
            style = shared.prompt_styles.styles[k]
            styleList.append({"name":style[0], "prompt": style[1], "negative_prompt": style[2]})

        return styleList

    def get_embeddings(self):
        # Return empty for remote API
        return {"loaded": {}, "skipped": {}}

    def refresh_embeddings(self):
        # Not applicable for remote API
        pass

    def refresh_checkpoints(self):
        # Not applicable for remote API
        pass

    def refresh_vae(self):
        # Not applicable for remote API
        pass

    def create_embedding(self, args: dict):
        # Not applicable for remote API
        return models.CreateResponse(info="Not supported in remote API mode")

    def create_hypernetwork(self, args: dict):
        # Not applicable for remote API
        return models.CreateResponse(info="Not supported in remote API mode")

    def train_embedding(self, args: dict):
        # Not applicable for remote API
        return models.TrainResponse(info="Not supported in remote API mode")

    def train_hypernetwork(self, args: dict):
        # Not applicable for remote API
        return models.TrainResponse(info="Not supported in remote API mode")

    def get_memory(self):
        try:
            import os
            import psutil
            process = psutil.Process(os.getpid())
            res = process.memory_info()
            ram_total = 100 * res.rss / process.memory_percent()
            ram = { 'free': ram_total - res.rss, 'used': res.rss, 'total': ram_total }
        except Exception as err:
            ram = { 'error': f'{err}' }
        
        # CUDA not available in remote API mode
        cuda = {'error': 'Not available in remote API mode'}
        return models.MemoryResponse(ram=ram, cuda=cuda)

    def get_extensions_list(self):
        from modules import extensions
        extensions.list_extensions()
        ext_list = []
        for ext in extensions.extensions:
            ext: extensions.Extension
            ext.read_info_from_repo()
            if ext.remote is not None:
                ext_list.append({
                    "name": ext.name,
                    "remote": ext.remote,
                    "branch": ext.branch,
                    "commit_hash":ext.commit_hash,
                    "commit_date":ext.commit_date,
                    "version":ext.version,
                    "enabled":ext.enabled
                })
        return ext_list

    def launch(self, server_name, port, root_path):
        self.app.include_router(self.router)
        uvicorn.run(
            self.app,
            host=server_name,
            port=port,
            timeout_keep_alive=shared.cmd_opts.timeout_keep_alive,
            root_path=root_path,
            ssl_keyfile=shared.cmd_opts.tls_keyfile,
            ssl_certfile=shared.cmd_opts.tls_certfile
        )

    def kill_webui(self):
        restart.stop_program()

    def restart_webui(self):
        if restart.is_restartable():
            restart.restart_program()
        return Response(status_code=501)

    def stop_webui(request):
        shared.state.server_command = "stop"
        return Response("Stopping.")

