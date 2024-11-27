import logging
from typing import Dict, Optional
import json

from config.ollama_config import (
    OLLAMA_CONFIG,
    PROMPT_CONFIG,
    get_generation_params,
    get_context_params,
    get_history_params
)
from services.ollama_connection import OllamaConnection

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class OllamaService:
    def __init__(self):
        self.base_url = OLLAMA_CONFIG["base_url"]
        self.model = OLLAMA_CONFIG["model"]
        self.story_context = []
        self.used_phrases = set()
        self.scene_history = []
        self.is_error_state = False
        self.connection = OllamaConnection(self.base_url)
        self.context_params = get_context_params()
        self.history_params = get_history_params()
        logger.info(f"OllamaService initialized with model: {self.model}")

    async def generate_story_prompt(self) -> str:
        """Генерирует промпт для создания новой истории"""
        return f"""[INST] {PROMPT_CONFIG['system_context']}
        
        Напиши на русском языке начало интересной истории.
        
        Стиль повествования:
        - Тон: {PROMPT_CONFIG['style_guidelines']['tone']}
        - Темп: {PROMPT_CONFIG['style_guidelines']['pacing']}
        - Описания: {PROMPT_CONFIG['style_guidelines']['description_style']}
        - Диалоги: {PROMPT_CONFIG['style_guidelines']['dialog_style']}
        
        Требования к истории:
        1. Интригующее начало
        2. Яркий главный персонаж с уникальным характером
        3. Четкое описание места действия
        4. Намек на будущий конфликт или тайну
        
        Ответь строго в формате JSON:
        {{
            "scene_description": "детальное описание места действия, которое можно визуализировать",
            "character_name": "имя главного персонажа",
            "character_description": "внешность и характер персонажа",
            "initial_situation": "описание начальной ситуации",
            "mood": "общее настроение сцены",
            "time_of_day": "время суток"
        }} [/INST]"""

    async def generate_next_prompt(self, current_context: str) -> str:
        """Генерирует промпт для следующей части истории"""
        # Анализируем последние события
        recent_events = self.analyze_recent_events()
        
        return f"""[INST] {PROMPT_CONFIG['system_context']}
        
        Текущий контекст истории:
        {current_context}
        
        Последние события:
        {recent_events}
        
        Продолжи историю, развивая её в соответствии с последним выбором. 
        
        СТРОГИЕ ПРАВИЛА:
        1. КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО повторять предыдущие сцены и диалоги
        2. История ВСЕГДА должна развиваться вперёд, никаких возвратов назад
        3. Каждая сцена должна быть АБСОЛЮТНО уникальной
        4. Учитывай эмоциональное состояние и развитие персонажа
        5. Создавай НОВЫЕ ситуации, а не вариации предыдущих
        6. Каждый диалог должен ПРОДВИГАТЬ сюжет
        7. Избегай общих фраз и клише
        8. Не используй фразы, которые уже были в истории
        
        Требования к продолжению:
        1. Детальное описание КОНКРЕТНЫХ последствий сделанного выбора
        2. Глубокая эмоциональная реакция персонажа
        3. Значимые изменения в окружении
        4. Развитие сюжета через уникальный диалог
        5. 2-3 КОНТРАСТНЫХ варианта для следующего выбора
        
        Ответь строго в формате JSON:
        {{
            "scene_description": "подробное описание НОВОЙ сцены и значимых изменений",
            "character_name": "имя говорящего персонажа",
            "dialog": "содержательный диалог или мысли, продвигающие сюжет",
            "emotion": "текущая эмоция персонажа",
            "mood": "атмосфера сцены",
            "time_of_day": "время суток",
            "choices": [
                {{"text": "вариант 1 - уникальное действие", "consequence": "описание важных последствий"}},
                {{"text": "вариант 2 - контрастное действие", "consequence": "описание важных последствий"}},
                {{"text": "вариант 3 - неожиданное действие", "consequence": "описание важных последствий"}}
            ]
        }} [/INST]"""

    def analyze_recent_events(self) -> str:
        """Анализирует последние события для улучшения контекста"""
        if not self.story_context:
            return "История только начинается."
        
        recent = self.story_context[-5:]
        analysis = []
        
        for event in recent:
            if event["type"] == "scene":
                analysis.append(f"Текущая обстановка: {event['content']}")
            elif event["type"] == "dialog":
                analysis.append(f"Последний диалог: {event['content']}")
            elif event["type"] == "choice":
                analysis.append(f"Выбор игрока: {event['content']}")
        
        return "\n".join(analysis)

    def is_repetitive(self, text: str) -> bool:
        """Проверяет текст на повторы"""
        # Разбиваем текст на фразы
        phrases = [p.strip() for p in text.split('.') if p.strip()]
        
        for phrase in phrases:
            if phrase in self.used_phrases:
                return True
            if any(self.similar_phrases(phrase, used) for used in self.used_phrases):
                return True
        
        # Добавляем новые фразы в использованные
        self.used_phrases.update(phrases)
        return False

    def similar_phrases(self, phrase1: str, phrase2: str) -> bool:
        """Проверяет схожесть фраз"""
        # Простое сравнение на основе общих слов
        words1 = set(word.lower() for word in phrase1.split())
        words2 = set(word.lower() for word in phrase2.split())
        
        common_words = words1.intersection(words2)
        total_words = len(words1.union(words2))
        
        if total_words == 0:
            return False
            
        similarity = len(common_words) / total_words
        return similarity > 0.7  # Порог схожести

    def is_technical_message(self, message: Dict) -> bool:
        """Проверяет, является ли сообщение техническим"""
        if not isinstance(message, dict):
            return False
            
        # Проверяем признаки технического сообщения
        technical_indicators = [
            message.get('character_name') == 'Система',
            'ошибка' in message.get('scene_description', '').lower(),
            'error' in message.get('mood', '').lower(),
            'техническое' in message.get('mood', '').lower(),
            'не удалось подключиться' in message.get('dialog', '').lower(),
            'попробовать снова' in str(message.get('choices', '')).lower()
        ]
        
        return any(technical_indicators)

    def add_to_story_context(self, event_type: str, content: str, metadata: Dict = None) -> None:
        """Добавляет событие в контекст истории с проверкой на технические сообщения"""
        # Не добавляем событие, если мы находимся в состоянии ошибки
        if self.is_error_state:
            logger.debug(f"Skipping event addition due to error state: {event_type} - {content[:50]}...")
            return

        # Создаем событие
        event = {
            "type": event_type,
            "content": content,
            "timestamp": len(self.story_context)
        }
        
        if metadata:
            event.update(metadata)

        # Добавляем событие в контекст
        self.story_context.append(event)
        logger.debug(f"Added event to context: {event_type} - {content[:50]}...")

    async def generate(self, prompt: str) -> Dict:
        """Отправляет запрос к Ollama API и получает ответ"""
        logger.debug(f"Sending request to Ollama API with prompt: {prompt[:100]}...")
        
        request_data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": get_generation_params()
        }
        
        try:
            result = await self.connection.make_request(
                "post",
                "/api/generate",
                request_data
            )
            
            if result and "response" in result:
                try:
                    # Пытаемся распарсить JSON из ответа
                    return json.loads(result['response'])
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse JSON from response: {e}")
                    # Если не получилось распарсить JSON, пробуем найти JSON в тексте
                    text = result['response']
                    try:
                        # Ищем начало и конец JSON
                        start = text.find('{')
                        end = text.rfind('}') + 1
                        if start >= 0 and end > start:
                            json_str = text[start:end]
                            logger.debug(f"Extracted JSON string: {json_str}")
                            return json.loads(json_str)
                    except Exception as e:
                        logger.error(f"Failed to extract JSON from text: {e}")
                    
                    return self.create_error_response(f"Ошибка парсинга ответа: {str(e)}")
            else:
                return self.create_error_response("Неверный формат ответа от сервера")
                
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
            return self.create_error_response(f"Ошибка генерации: {str(e)}")

    def create_error_response(self, error_message: str) -> Dict:
        """Создает структурированный ответ с ошибкой"""
        return {
            "scene_description": "Произошла ошибка при генерации",
            "character_name": "Система",
            "dialog": "Пожалуйста, подождите...",
            "emotion": "neutral",
            "mood": "technical",
            "time_of_day": "не указано",
            "choices": [
                {"text": "Продолжить", "consequence": "Повторная попытка генерации"}
            ]
        }

    async def start_new_story(self) -> Dict:
        """Генерирует начало новой истории"""
        logger.info("Starting new story generation")
        self.story_context = []  # Очищаем контекст
        prompt = await self.generate_story_prompt()
        result = await self.generate(prompt)
        
        if "error" not in result:
            # Сохраняем начало истории в контекст
            if result.get('scene_description'):
                self.add_to_story_context("scene", result['scene_description'])
            if result.get('character_name'):
                self.add_to_story_context("character", result['character_name'])
            if result.get('character_description'):
                self.add_to_story_context("character_description", result['character_description'])
            if result.get('initial_situation'):
                self.add_to_story_context("initial_situation", result['initial_situation'])
            logger.info("Successfully generated story start")
            logger.debug(f"Initial context: {self.story_context}")
        else:
            logger.error(f"Failed to generate story start: {result.get('error')}")
        
        return result

    async def generate_next_scene(self, selected_choice: Optional[str] = None) -> Dict:
        """Генерирует следующую сцену истории"""
        logger.info(f"Generating next scene with choice: {selected_choice}")
        
        try:
            if selected_choice:
                # Проверяем, не является ли выбор техническим (например, "Попробовать снова")
                if not any(tech_phrase in selected_choice.lower() 
                          for tech_phrase in ['попробовать снова', 'повторить', 'перезапустить']):
                    self.add_to_story_context("choice", selected_choice)
            
            # Форматируем контекст
            formatted_context = []
            for item in self.story_context[-5:]:
                if isinstance(item, dict):
                    if item["type"] == "choice":
                        formatted_context.append(f"Выбор игрока: {item['content']}")
                    elif item["type"] == "scene":
                        formatted_context.append(f"Сцена: {item['content']}")
                    elif item["type"] == "dialog":
                        formatted_context.append(f"Диалог: {item['content']}")
            
            # Генерируем новую сцену
            prompt = await self.generate_next_prompt("\n".join(formatted_context))
            result = await self.generate(prompt)
            
            if "error" not in result and not self.is_technical_message(result):
                self.is_error_state = False  # Сбрасываем флаг ошибки при успешной генерации
                
                # Проверяем на повторы
                if result.get('scene_description'):
                    if self.is_repetitive(result['scene_description']):
                        logger.warning("Detected scene repetition, requesting regeneration")
                        return await self.generate_next_scene(selected_choice)
                    
                    self.add_to_story_context("scene", result['scene_description'])
                    
                if result.get('dialog'):
                    if self.is_repetitive(result['dialog']):
                        logger.warning("Detected dialog repetition, requesting regeneration")
                        return await self.generate_next_scene(selected_choice)
                    
                    self.add_to_story_context("dialog", result['dialog'])
            else:
                self.is_error_state = True  # Устанавливаем флаг ошибки
                logger.error("Generated content was technical or contained an error")
                result = {
                    "scene_description": "Произошла ошибка при генерации",
                    "character_name": "Система",
                    "dialog": "Пожалуйста, подождите...",
                    "emotion": "neutral",
                    "mood": "technical",
                    "time_of_day": "не указано",
                    "choices": [
                        {"text": "Продолжить", "consequence": "Повторная попытка генерации"}
                    ]
                }
            
            return result
            
        except Exception as e:
            self.is_error_state = True  # Устанавливаем флаг ошибки
            logger.error(f"Error in generate_next_scene: {str(e)}")
            return {
                "scene_description": "Произошла ошибка",
                "character_name": "Система",
                "dialog": "Пожалуйста, подождите...",
                "emotion": "neutral",
                "mood": "technical",
                "time_of_day": "не указано",
                "choices": [
                    {"text": "Продолжить", "consequence": "Повторная попытка генерации"}
                ]
            }

    async def trim_history(self) -> None:
        """Обрезает историю, если она слишком длинная"""
        if len(self.story_context) > self.history_params["max_history_size"]:
            logger.info(f"Trimming history from {len(self.story_context)} to {self.history_params['trim_size']}")
            self.story_context = self.story_context[-self.history_params["trim_size"]:]
