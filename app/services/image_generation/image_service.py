import aiohttp
import json
import asyncio
import logging
import os
import base64
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ImageGenerationError(Exception):
    """Базовый класс для ошибок генерации изображений"""
    pass

class ResourceError(ImageGenerationError):
    """Ошибки, связанные с ресурсами (память, GPU и т.д.)"""
    pass

class APIError(ImageGenerationError):
    """Ошибки API ComfyUI"""
    pass

class GenerationStatus(Enum):
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class GenerationResult:
    status: GenerationStatus
    image_data: Optional[str] = None
    error_message: Optional[str] = None

class ImageGenerationService:
    def __init__(self):
        self.base_url = os.getenv("COMFYUI_API_URL", "http://127.0.0.1:8188")
        self.base_prompt = os.getenv("COMFYUI_BASE_PROMPT", "anime style, high quality illustration")
        self.min_memory_gb = float(os.getenv("COMFYUI_MIN_MEMORY_GB", "2.0"))
        
    async def check_system_resources(self, session: aiohttp.ClientSession) -> Tuple[bool, str]:
        """Проверяет доступность системных ресурсов"""
        try:
            async with session.get(f"{self.base_url}/system_stats") as response:
                if response.status != 200:
                    return False, "Не удалось получить информацию о системе"
                
                stats = await response.json()
                if 'system' in stats and 'memory' in stats['system']:
                    memory_info = stats['system']['memory']
                    free_memory = memory_info.get('free', 0)
                    total_memory = memory_info.get('total', 0)
                    
                    free_memory_gb = free_memory / (1024 * 1024 * 1024)
                    if free_memory_gb < self.min_memory_gb:
                        return False, f"Недостаточно памяти GPU: {free_memory_gb:.2f}GB < {self.min_memory_gb}GB"
                    
                    return True, ""
                
                return False, "Не удалось получить информацию о памяти"
        except Exception as e:
            return False, f"Ошибка проверки ресурсов: {str(e)}"

    async def prepare_workflow(self, prompt: str, session: aiohttp.ClientSession) -> Dict:
        """Подготавливает workflow для генерации"""
        try:
            # Здесь должна быть логика модификации workflow из comfy_config
            # Пока используем заглушку
            return {
                "prompt": f"{self.base_prompt}, {prompt}",
                "workflow": {}  # Здесь должен быть реальный workflow
            }
        except Exception as e:
            raise APIError(f"Ошибка подготовки workflow: {str(e)}")

    async def wait_for_generation(
        self, 
        prompt_id: str, 
        session: aiohttp.ClientSession,
        timeout: int = 300,
        check_interval: int = 1
    ) -> str:
        """Ожидает завершения генерации изображения"""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError("Превышено время ожидания генерации")
                
            try:
                async with session.get(f"{self.base_url}/history/{prompt_id}") as response:
                    if response.status != 200:
                        raise APIError(f"Ошибка получения статуса: {response.status}")
                        
                    history = await response.json()
                    if prompt_id in history:
                        outputs = history[prompt_id].get('outputs', {})
                        if outputs and '9' in outputs:
                            image_data = outputs['9']
                            if image_data and 'images' in image_data:
                                return image_data['images'][0]['filename']
                                
            except aiohttp.ClientError as e:
                raise APIError(f"Ошибка сети при проверке статуса: {str(e)}")
                
            await asyncio.sleep(check_interval)

    async def get_image_data(self, image_path: str, session: aiohttp.ClientSession) -> str:
        """Получает данные изображения в формате base64"""
        try:
            image_url = f"{self.base_url}/view?filename={image_path}"
            async with session.get(image_url) as response:
                if response.status != 200:
                    raise APIError(f"Ошибка получения изображения: {response.status}")
                    
                img_data = await response.read()
                return f"data:image/png;base64,{base64.b64encode(img_data).decode('utf-8')}"
        except Exception as e:
            raise APIError(f"Ошибка при получении данных изображения: {str(e)}")

    async def generate_image(self, prompt: str, session: Optional[aiohttp.ClientSession] = None) -> GenerationResult:
        """Основной метод генерации изображения"""
        own_session = session is None
        if own_session:
            session = aiohttp.ClientSession()
            
        try:
            # Проверяем ресурсы
            resources_ok, error_message = await self.check_system_resources(session)
            if not resources_ok:
                return GenerationResult(
                    status=GenerationStatus.FAILED,
                    error_message=error_message
                )

            # Подготавливаем и отправляем workflow
            workflow = await self.prepare_workflow(prompt, session)
            async with session.post(
                f"{self.base_url}/prompt",
                json={"prompt": workflow}
            ) as response:
                if response.status != 200:
                    return GenerationResult(
                        status=GenerationStatus.FAILED,
                        error_message=f"Ошибка запуска генерации: {response.status}"
                    )
                
                prompt_id = (await response.json())['prompt_id']

            # Ожидаем результат
            try:
                image_path = await self.wait_for_generation(prompt_id, session)
                image_data = await self.get_image_data(image_path, session)
                
                return GenerationResult(
                    status=GenerationStatus.COMPLETED,
                    image_data=image_data
                )
                
            except TimeoutError as e:
                return GenerationResult(
                    status=GenerationStatus.FAILED,
                    error_message=str(e)
                )
            except APIError as e:
                return GenerationResult(
                    status=GenerationStatus.FAILED,
                    error_message=str(e)
                )
                
        except Exception as e:
            return GenerationResult(
                status=GenerationStatus.FAILED,
                error_message=f"Неожиданная ошибка: {str(e)}"
            )
            
        finally:
            if own_session:
                await session.close()

# Создаем глобальный экземпляр сервиса
image_service = ImageGenerationService()
