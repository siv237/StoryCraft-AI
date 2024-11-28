import aiohttp
import json
import asyncio
from typing import Dict, Optional
import logging
from config.comfy_config import comfy_config
from config.ollama_config import OLLAMA_CONFIG

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StoryImageGenerator:
    def __init__(self):
        self.ollama_url = OLLAMA_CONFIG['base_url']
        self.model = OLLAMA_CONFIG['model']
        
    async def _translate_to_english(self, text: str) -> str:
        """Переводит текст на английский язык используя Ollama"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                system_prompt = """You are a professional translator. Translate the following text from Russian to English.
                Focus on descriptive elements that would be useful for image generation.
                Return ONLY the translation, without any additional text or explanations.
                Make the translation more visual and descriptive."""
                
                timeout = aiohttp.ClientTimeout(total=30)  # Увеличиваем таймаут до 30 секунд
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                        f"{self.ollama_url}/api/generate",
                        json={
                            "model": self.model,
                            "system": system_prompt,
                            "prompt": text,
                            "stream": False,
                            "temperature": 0.1,
                        }
                    ) as response:
                        if response.status != 200:
                            logger.error(f"Попытка {attempt + 1}: Ошибка перевода, статус {response.status}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(retry_delay * (attempt + 1))
                                continue
                            return self._fallback_translation(text)
                        
                        result = await response.json()
                        return result['response'].strip()
                        
            except Exception as e:
                logger.error(f"Попытка {attempt + 1}: Ошибка перевода: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue
                return self._fallback_translation(text)
        
        return self._fallback_translation(text)

    def _fallback_translation(self, text: str) -> str:
        """Резервный метод перевода - простая обработка текста для генерации изображения"""
        # Удаляем специальные символы и маркеры
        text = text.replace('**', '').replace('[DONE]', '').strip()
        # Добавляем базовые дескрипторы для улучшения генерации
        return f"scene with characters, story illustration, {text}"

    def _extract_scene_description(self, text: str) -> str:
        """Извлекает описание сцены из текста"""
        # Разбиваем на предложения и берем последние 2-3
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        relevant_sentences = sentences[-3:] if len(sentences) > 3 else sentences
        return '. '.join(relevant_sentences)

    async def _prepare_image_prompt(self, context: Dict) -> str:
        """Подготавливает промпт для генерации изображения на основе контекста истории"""
        # Получаем текущий текст и описание сцены
        current_text = context.get('current_text', '')
        scene_description = self._extract_scene_description(current_text)
        
        # Переводим на английский
        eng_context = await self._translate_to_english(scene_description)
        
        # Формируем промпт для изображения
        base_prompt = "book illustration, detailed artistic scene, high quality, masterpiece"
        prompt = f"{base_prompt}, {eng_context}"
        
        logger.info(f"Подготовлен промпт для изображения: {prompt}")
        return prompt

    async def generate_story_illustration(self, context: Dict) -> Optional[str]:
        """Генерирует иллюстрацию для текущего момента истории"""
        try:
            # Подготавливаем промпт
            prompt = await self._prepare_image_prompt(context)
            
            # Модифицируем workflow с нашим промптом
            workflow = comfy_config.modify_workflow(
                prompt=prompt,
                seed=None,  # Используем случайный сид для разнообразия
                width=768,
                height=512
            )
            
            # Отправляем запрос на генерацию
            async with aiohttp.ClientSession() as session:
                # Запускаем workflow
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
                                            logger.info(f"Изображение сгенерировано: {image_path}")
                                            return image_path
                                    break
                            
                        await asyncio.sleep(1)  # Пауза между проверками
                        
            return None
            
        except Exception as e:
            logger.error(f"Ошибка генерации иллюстрации: {e}")
            return None

# Создаем экземпляр генератора изображений
story_image_generator = StoryImageGenerator()
