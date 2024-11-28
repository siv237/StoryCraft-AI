from typing import Dict, Any, Optional
import requests
import json
import os
from dataclasses import dataclass

@dataclass
class ComfyUIConfig:
    host: str = "127.0.0.1"
    port: int = 8188
    base_url: str = "http://127.0.0.1:8188"
    
    # Базовый конфиг для генерации изображений
    default_workflow: Dict[str, Any] = None
    
    def __post_init__(self):
        self.base_url = f"http://{self.host}:{self.port}"
        self.default_workflow = {
            "3": {
                "inputs": {
                    "seed": 92494398233826,
                    "steps": 10,          # Уменьшили количество шагов
                    "cfg": 7,
                    "sampler_name": "euler_ancestral",
                    "scheduler": "karras",
                    "denoise": 1,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                },
                "class_type": "KSampler",
                "_meta": {
                    "title": "KSampler"
                }
            },
            "4": {
                "inputs": {
                    "ckpt_name": "CrowPonyQp_ponyV3.safetensors"  # Стабильная модель, хорошо работает
                },
                "class_type": "CheckpointLoaderSimple",
                "_meta": {
                    "title": "Load Checkpoint"
                }
            },
            "5": {
                "inputs": {
                    "width": 384,         # Уменьшили разрешение
                    "height": 384,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage",
                "_meta": {
                    "title": "Empty Latent Image"
                }
            },
            "6": {
                "inputs": {
                    "text": "",
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {
                    "title": "CLIP Text Encode (Prompt)"
                }
            },
            "7": {
                "inputs": {
                    "text": "text, watermark, bad quality, blurry, nsfw",
                    "clip": ["4", 1]
                },
                "class_type": "CLIPTextEncode",
                "_meta": {
                    "title": "CLIP Text Encode (Negative Prompt)"
                }
            },
            "8": {
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                },
                "class_type": "VAEDecode",
                "_meta": {
                    "title": "VAE Decode"
                }
            },
            "9": {
                "inputs": {
                    "filename_prefix": "ComfyUI",
                    "images": ["8", 0]
                },
                "class_type": "SaveImage",
                "_meta": {
                    "title": "Save Image"
                }
            }
        }

    def check_connection(self) -> bool:
        """Проверка доступности ComfyUI сервера"""
        try:
            response = requests.get(f"{self.base_url}/system_stats")
            return response.status_code == 200
        except requests.RequestException:
            return False

    def get_model_list(self) -> Optional[Dict[str, Any]]:
        """Получение списка доступных моделей"""
        try:
            response = requests.get(f"{self.base_url}/object_info")
            if response.status_code == 200:
                return response.json()
            return None
        except requests.RequestException:
            return None

    def modify_workflow(self, prompt: str, seed: Optional[int] = None,
                       width: int = 384, height: int = 384) -> Dict[str, Any]:
        """Модификация рабочего процесса с пользовательскими параметрами"""
        workflow = self.default_workflow.copy()
        
        # Обновляем параметры
        if seed is not None:
            workflow["3"]["inputs"]["seed"] = seed
        
        # Ограничиваем размеры для экономии памяти
        width = min(width, 384)    # Уменьшили максимальный размер
        height = min(height, 384)
        
        workflow["5"]["inputs"]["width"] = width
        workflow["5"]["inputs"]["height"] = height
        workflow["6"]["inputs"]["text"] = prompt
        
        return workflow

# Создаем экземпляр конфигурации
comfy_config = ComfyUIConfig()
