import aiohttp
import json
import asyncio
from typing import Dict, Optional
import logging
from config.comfy_config import comfy_config
from config.ollama_config import OLLAMA_CONFIG, PROMPT_CONFIG
import base64
import os

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StoryImageGenerator:
    def __init__(self):
        # Убираем дублирование, используем конфиг напрямую
        pass
        
    async def _translate_to_english(self, text: str, session: aiohttp.ClientSession) -> str:
        """Переводит текст на английский язык и создает краткое описание сцены"""
        max_retries = OLLAMA_CONFIG['connection']['max_retries']
        retry_delay = OLLAMA_CONFIG['connection']['retry_delay']
        
        system_prompt = """Create a very short scene description in English"""

        for attempt in range(max_retries):
            try:
                async with session.post(
                    f"{OLLAMA_CONFIG['base_url']}/api/generate",
                    json={
                        "model": OLLAMA_CONFIG['model'],
                        "system": system_prompt,
                        "prompt": text,
                        **OLLAMA_CONFIG['generation_params'],
                        "stream": True
                    }
                ) as response:
                    if response.status != 200:
                        logger.error(f"Попытка {attempt + 1}: Ошибка перевода, статус {response.status}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay * (attempt + 1))
                            continue
                        return self._fallback_translation(text)
                    
                    translation = ""
                    async for line in response.content:
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                translation += data["response"]
                        except json.JSONDecodeError:
                            continue
                    
                    return translation.strip()
                    
            except Exception as e:
                logger.error(f"Попытка {attempt + 1}: Ошибка перевода: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue
                return self._fallback_translation(text)
        
        return self._fallback_translation(text)

    def _fallback_translation(self, text: str) -> str:
        """Резервный метод перевода - простая обработка текста для генерации изображения"""
        # Возвращаем самое базовое описание
        return "character in a room, story scene"

    async def _prepare_image_prompt(self, context: Dict, session: aiohttp.ClientSession) -> str:
        """Подготавливает промпт для генерации изображения на основе контекста истории"""
        # Получаем текущий текст
        current_text = context.get('current_text', '')
        
        # Получаем краткое описание на английском
        eng_description = await self._translate_to_english(current_text, session)
        
        # Формируем промпт для изображения
        base_prompt = "anime style, high quality illustration"
        prompt = f"{base_prompt}, {eng_description}"
        
        logger.info(f"Подготовлен промпт для изображения: {prompt}")
        return prompt

    async def _unload_all_models(self) -> None:
        """Выгружает все загруженные модели из GPU"""
        try:
            # Получаем список всех моделей
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{comfy_config.base_url}/object_info/CheckpointLoaderSimple") as response:
                    if response.status != 200:
                        logger.error("Не удалось получить список моделей")
                        return
                    
                    model_info = await response.json()
                    if not model_info or 'CheckpointLoaderSimple' not in model_info:
                        return
                    
                    models = model_info['CheckpointLoaderSimple']['input']['required']['ckpt_name'][0]
                    logger.info(f"Доступные модели: {', '.join(models)}")

                # Очищаем память
                async with session.post(
                    f"{comfy_config.base_url}/queue",
                    json={"clear": True}
                ) as clear_response:
                    if clear_response.status == 200:
                        logger.info("Очередь генерации очищена")
                    
                async with session.post(
                    f"{comfy_config.base_url}/free",
                    json={}
                ) as free_response:
                    if free_response.status == 200:
                        logger.info("Все модели выгружены из GPU")

        except Exception as e:
            logger.error(f"Ошибка при выгрузке моделей: {e}")

    async def generate_story_illustration(self, context: Dict) -> Optional[str]:
        """Генерирует иллюстрацию для текущего сегмента истории"""
        try:
            session = context.get('session')
            if not session:
                # Если сессия не передана, создаем новую
                session = aiohttp.ClientSession()
                need_close = True
            else:
                need_close = False

            try:
                # Используем готовый промпт из контекста
                prompt = context.get('prompt', 'character in a room, story scene')
                base_prompt = "anime style, high quality illustration"
                full_prompt = f"{base_prompt}, {prompt}"
                
                # Проверяем доступную память GPU
                async with session.get(f"{comfy_config.base_url}/system_stats") as response:
                    if response.status != 200:
                        logger.error("Не удалось получить информацию о системе")
                        return None
                    
                    stats = await response.json()
                    if 'system' in stats and 'memory' in stats['system']:
                        memory_info = stats['system']['memory']
                        free_memory = memory_info.get('free', 0)
                        total_memory = memory_info.get('total', 0)
                        
                        # Если свободной памяти меньше 2GB, пропускаем генерацию
                        if free_memory < 2 * 1024 * 1024 * 1024:  # 2GB в байтах
                            logger.warning("Недостаточно свободной памяти GPU для генерации изображения")
                            return None
            
                # Модифицируем workflow с нашим промптом
                workflow = comfy_config.modify_workflow(
                    prompt=full_prompt,
                    seed=None,  # Используем случайный сид для разнообразия
                    width=384,  # Уменьшенный размер для экономии памяти
                    height=384
                )
                
                # Отправляем запрос на генерацию
                async with session.post(
                    f"{comfy_config.base_url}/prompt",
                    json={"prompt": workflow}
                ) as response:
                    if response.status != 200:
                        logger.error(f"Ошибка запуска workflow: {await response.text()}")
                        return None
                    
                    prompt_id = (await response.json())['prompt_id']
                    logger.info(f"Запущена генерация изображения, prompt_id: {prompt_id}")
                    
                    # Ждем завершения генерации
                    while True:
                        async with session.get(f"{comfy_config.base_url}/history/{prompt_id}") as status_response:
                            if status_response.status != 200:
                                continue
                                
                            history = await status_response.json()
                            if prompt_id in history:
                                if 'outputs' in history[prompt_id]:
                                    # Получаем путь к сгенерированному изображению
                                    outputs = history[prompt_id]['outputs']
                                    if outputs and '9' in outputs:  # '9' - это node SaveImage
                                        image_data = outputs['9']
                                        if image_data and 'images' in image_data:
                                            image_path = image_data['images'][0]['filename']
                                            
                                            # Получаем изображение через API
                                            try:
                                                image_url = f"{comfy_config.base_url}/view?filename={image_path}"
                                                async with session.get(image_url) as response:
                                                    if response.status == 200:
                                                        img_data = await response.read()
                                                        base64_img = base64.b64encode(img_data).decode('utf-8')
                                                        return f"data:image/png;base64,{base64_img}"
                                                    else:
                                                        logger.error(f"Ошибка при получении изображения: {response.status}")
                                                        return None
                                            except Exception as e:
                                                logger.error(f"Ошибка при получении изображения: {e}")
                                                return None
                                    break
                            
                        await asyncio.sleep(1)  # Пауза между проверками
                        
            finally:
                if need_close:
                    await session.close()
                    
        except Exception as e:
            logger.error(f"Ошибка генерации иллюстрации: {e}")
            return None

# Создаем экземпляр генератора изображений
story_image_generator = StoryImageGenerator()
