# Stable Diffusion WebUI Proxy Mode

This is a lightweight proxy version of Stable Diffusion WebUI that delegates all image generation to a remote Stable Diffusion API endpoint while keeping the full Gradio interface.

## Features

- Full Gradio WebUI interface
- All generation requests proxied to remote SD API
- No local model loading or heavy ML dependencies
- Docker support for easy deployment
- Environment variable configuration

## Quick Start

### Using Docker

1. Build the Docker image:
```bash
docker build -t sd-webui-proxy .
```

2. Run the container:
```bash
docker run -p 7860:7860 -e SD_API_URL=http://your-sd-server:7860 sd-webui-proxy
```

### Using Python directly

1. Set the environment variable:
```bash
export SD_API_URL=http://your-sd-server:7860
```

2. Run the WebUI:
```bash
python webui.py --listen --api
```

## Configuration

### Environment Variables

- `SD_API_URL`: URL of the remote Stable Diffusion API server (default: `http://localhost:7860`)
- `SD_API_TIMEOUT`: Timeout for API requests in seconds (default: `300`)
- `GRADIO_SERVER_NAME`: Server hostname (default: `0.0.0.0`)
- `GRADIO_SERVER_PORT`: Server port (default: `7860`)

### Docker Environment Variables

```bash
docker run -p 7860:7860 \
  -e SD_API_URL=http://your-sd-server:7860 \
  -e SD_API_TIMEOUT=600 \
  -e GRADIO_SERVER_PORT=7860 \
  sd-webui-proxy
```

## API Endpoints

The proxy supports all standard SD WebUI API endpoints:

- `/sdapi/v1/txt2img` - Text to image generation
- `/sdapi/v1/img2img` - Image to image generation
- `/sdapi/v1/extra-single-image` - Single image upscaling
- `/sdapi/v1/extra-batch-images` - Batch image upscaling
- `/sdapi/v1/png-info` - PNG metadata extraction
- `/sdapi/v1/progress` - Generation progress
- `/sdapi/v1/interrogate` - Image interrogation
- `/sdapi/v1/interrupt` - Interrupt generation
- `/sdapi/v1/skip` - Skip current generation

## Architecture

```
┌─────────────────┐    HTTP API    ┌─────────────────┐
│   WebUI Proxy   │ ──────────────► │  Remote SD API  │
│                 │                │                 │
│ - Gradio UI     │                │ - Model Loading │
│ - API Proxy     │                │ - Generation    │
│ - No Models    │                │ - Processing    │
└─────────────────┘                └─────────────────┘
```

## Benefits

1. **Lightweight**: No local model loading, minimal dependencies
2. **Scalable**: Can handle multiple proxy instances
3. **Flexible**: Easy to switch between local and remote processing
4. **Resource Efficient**: Low memory and CPU usage
5. **Docker Ready**: Easy deployment and scaling

## Development

### Local Development

1. Set up a remote SD server
2. Set `SD_API_URL` environment variable
3. Run `python webui.py --listen --api`

### Testing

Test the proxy by making API calls:

```bash
curl -X POST http://localhost:7860/sdapi/v1/txt2img \
  -H "Content-Type: application/json" \
  -d '{"prompt": "a beautiful landscape", "steps": 20}'
```

## Troubleshooting

### Common Issues

1. **Connection Refused**: Check that `SD_API_URL` points to a running SD server
2. **Timeout Errors**: Increase `SD_API_TIMEOUT` for long generations
3. **Model Not Found**: Ensure the remote server has the required models loaded

### Logs

Check Docker logs:
```bash
docker logs <container_id>
```

## Requirements

- Python 3.10+
- Remote Stable Diffusion WebUI server
- Network connectivity between proxy and remote server

## License

Same as the original Stable Diffusion WebUI project.
