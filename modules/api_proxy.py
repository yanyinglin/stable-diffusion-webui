import os
import requests
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class RemoteSDAPIClient:
    def __init__(self):
        self.base_url = os.getenv('SD_API_URL', 'http://localhost:7860')
        self.timeout = int(os.getenv('SD_API_TIMEOUT', '300'))  # 5 minutes default
        
    def txt2img(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call remote txt2img API"""
        url = f"{self.base_url}/sdapi/v1/txt2img"
        try:
            logger.info(f"Calling remote txt2img API at {url}")
            response = requests.post(url, json=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to call remote txt2img API: {e}")
            raise Exception(f"Remote API call failed: {e}")
    
    def img2img(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call remote img2img API"""
        url = f"{self.base_url}/sdapi/v1/img2img"
        try:
            logger.info(f"Calling remote img2img API at {url}")
            response = requests.post(url, json=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to call remote img2img API: {e}")
            raise Exception(f"Remote API call failed: {e}")
    
    def extras_single_image(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call remote extras single image API"""
        url = f"{self.base_url}/sdapi/v1/extra-single-image"
        try:
            logger.info(f"Calling remote extras API at {url}")
            response = requests.post(url, json=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to call remote extras API: {e}")
            raise Exception(f"Remote API call failed: {e}")
    
    def extras_batch_images(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call remote extras batch images API"""
        url = f"{self.base_url}/sdapi/v1/extra-batch-images"
        try:
            logger.info(f"Calling remote extras batch API at {url}")
            response = requests.post(url, json=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to call remote extras batch API: {e}")
            raise Exception(f"Remote API call failed: {e}")
    
    def interrogate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call remote interrogate API"""
        url = f"{self.base_url}/sdapi/v1/interrogate"
        try:
            logger.info(f"Calling remote interrogate API at {url}")
            response = requests.post(url, json=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to call remote interrogate API: {e}")
            raise Exception(f"Remote API call failed: {e}")
    
    def png_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call remote PNG info API"""
        url = f"{self.base_url}/sdapi/v1/png-info"
        try:
            logger.info(f"Calling remote PNG info API at {url}")
            response = requests.post(url, json=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to call remote PNG info API: {e}")
            raise Exception(f"Remote API call failed: {e}")
    
    def get_progress(self) -> Dict[str, Any]:
        """Get progress from remote API"""
        url = f"{self.base_url}/sdapi/v1/progress"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get progress from remote API: {e}")
            raise Exception(f"Remote API call failed: {e}")
    
    def interrupt(self) -> Dict[str, Any]:
        """Interrupt remote generation"""
        url = f"{self.base_url}/sdapi/v1/interrupt"
        try:
            response = requests.post(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to interrupt remote generation: {e}")
            raise Exception(f"Remote API call failed: {e}")
    
    def skip(self) -> Dict[str, Any]:
        """Skip current generation on remote"""
        url = f"{self.base_url}/sdapi/v1/skip"
        try:
            response = requests.post(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to skip remote generation: {e}")
            raise Exception(f"Remote API call failed: {e}")
