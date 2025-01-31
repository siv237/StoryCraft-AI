import aiohttp
import json
import os
import re
from typing import Dict, List
from config.ollama_config import OLLAMA_CONFIG
import logging
from app.services.comfy.image_generator import story_image_generator

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GPU Memory Management
def cleanup_gpu():
    """Force cleanup of GPU memory"""
    import gc
    gc.collect()
    try:
        # Перезапускаем Ollama сервис для освобождения GPU памяти
        import subprocess
        subprocess.run(["systemctl", "restart", "ollama"], check=True)
        logger.info("Ollama service restarted to free GPU memory")
    except Exception as e:
        logger.warning(f"Failed to restart Ollama service: {e}")

class ModelManager:
    def __init__(self):
        self.active_models = {}
        self.model_params = {
            "gpu_layers": 27,  # Количество слоев на GPU
            "num_gpu": 1,      # Количество GPU
            "gpu_memory_utilization": 0.8  # Процент использования памяти GPU
        }
    
    def get_model(self, model_name):
        """Get model with memory management"""
        if model_name not in self.active_models:
            try:
                self.active_models[model_name] = client.load_model(
                    model_name, 
                    params=self.model_params
                )
            except Exception as e:
                logger.error(f"Failed to load model {model_name}: {e}")
                cleanup_gpu()  # Пробуем очистить память и загрузить снова
                self.active_models[model_name] = client.load_model(
                    model_name, 
                    params=self.model_params
                )
                
        return self.active_models[model_name]
    
    def unload_model(self, model_name):
        """Explicitly unload a model"""
        if model_name in self.active_models:
            del self.active_models[model_name]
            cleanup_gpu()

model_manager = ModelManager()

async def unload_model_from_gpu():
    """Выгружает модель из GPU без её удаления"""
    try:
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                f"{OLLAMA_CONFIG['base_url']}/api/generate",
                json={
                    "model": OLLAMA_CONFIG['model'],
                    "prompt": "",
                    "keep_alive": 0
                }
            )
            if response.status == 200:
                data = await response.json()
                if data.get("done_reason") == "unload":
                    logger.info(f"Модель {OLLAMA_CONFIG['model']} выгружена из GPU")
                    return True
                else:
                    logger.warning(f"Неожиданный ответ при выгрузке модели: {data}")
                    return False
            else:
                logger.warning(f"Не удалось выгрузить модель из GPU: {await response.text()}")
                return False
    except Exception as e:
        logger.warning(f"Ошибка при выгрузке модели из GPU: {e}")
        return False

async def generate_text(prompt: str) -> str:
    """Генерирует текст с помощью языковой модели"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OLLAMA_CONFIG['base_url']}/api/generate",
                json={
                    "model": OLLAMA_CONFIG["model"],
                    "prompt": prompt,
                    "stream": False
                }
            ) as response:
                result = await response.json()
                return result["response"]
    except Exception as e:
        logger.error(f"Ошибка генерации текста: {e}")
        return ""

async def generate_next_segment(choice: str, context: Dict) -> Dict:
    logger.info("[GENERATOR] >>> Начинаем генерацию нового сегмента")
    logger.info(f"[GENERATOR] Выбор пользователя: {choice}")
    
    # Сначала выгружаем модели ComfyUI чтобы освободить память для Ollama
    logger.info("[GENERATOR] >>> Выгружаем модели ComfyUI")
    await story_image_generator._unload_all_models()
    logger.info("[GENERATOR] <<< Модели ComfyUI выгружены")

    # Создаем краткое описание текущего состояния истории
    logger.info("[GENERATOR] >>> Формируем состояние истории")
    
    # Добавляем информацию о персонаже
    character_info = []
    if 'character' in context:
        character = context['character']
        if character.get('gender'):
            character_info.append(f"Пол персонажа: {character['gender']}")
        if character.get('age'):
            character_info.append(f"Возраст персонажа: {character['age']}")
        if character.get('name'):
            character_info.append(f"Имя персонажа: {character['name']}")
    
    # Добавляем хронологию событий
    timeline_events = []
    if 'timeline' in context and context['timeline']:
        timeline_events = [f"- {event}" for event in context['timeline'][-5:]]  # Берем последние 5 событий
    
    story_state = "\\n".join([
        f"Текущая глава: {context['current_chapter']}",
        "",
        "Информация о персонаже:",
        *character_info,
        "",
        "Недавние события:",
        *timeline_events,
        "",
        f"Последние выборы:",
        *[f"- {c}" for c in context['previous_choices'][-3:]],
        f"\\nТекущий выбор: {choice}"
    ])
    logger.info("[GENERATOR] <<< Состояние истории сформировано")

    # Специальный промпт для первой главы
    if choice == "начало истории":
        logger.info("[GENERATOR] Используем промпт для первой главы")
        system_prompt = """Ты - талантливый русскоязычный писатель, мастер художественного описания, создающий захватывающие интерактивные истории на русском языке.
        Твоя задача - создать яркое, детальное и атмосферное начало истории, которое полностью погрузит читателя в мир повествования.
        
        ВАЖНЫЕ ПРАВИЛА для первой главы:
        0. ПИШИ СТРОГО НА РУССКОМ ЯЗЫКЕ! НИКОГДА не используй английский или другие языки!
        
        1. Создай подробное, красочное описание окружения (3-4 абзаца):
           - Опиши физическое пространство: архитектуру, природу, погоду, освещение
           - Добавь сенсорные детали: звуки, запахи, тактильные ощущения
           - Передай общую атмосферу и настроение места
        
        2. Представь главного героя (1-2 абзаца):
           - Опиши внешность, возраст, характерные черты
           - Покажи его текущее эмоциональное состояние
           - Намекни на его предысторию или мотивацию
        
        3. Создай интригующую ситуацию:
           - Введи элемент тайны или конфликта
           - Намекни на больший контекст происходящего
           - Заложи основу для дальнейшего развития сюжета
        
        4. Стилистические требования:
           - Используй богатый литературный русский язык
           - Применяй разнообразные художественные приёмы
           - Соблюдай баланс между описанием и действием
        
        5. В конце предложи 3 значимых варианта выбора:
           - Каждый выбор должен вести к существенно разным путям развития истории
           - Варианты должны быть интригующими и неочевидными
           - Выборы должны отражать возможные мотивации героя
        
        ВАЖНО: 
        - Сначала напиши полный текст истории, а затем отдельно в конце укажи варианты выбора
        - Весь текст ДОЛЖЕН быть написан ТОЛЬКО на русском языке!"""
        
        user_prompt = """Пожалуйста, начни новую захватывающую историю. 
        Создай глубокое погружение в мир через детальное описание места действия, 
        главного героя и ситуации, в которой он оказался."""
    else:
        logger.info("[GENERATOR] Используем стандартный промпт")
        system_prompt = """Ты - талантливый русскоязычный писатель, создающий захватывающие интерактивные истории.
        
        ВАЖНЫЕ ПРАВИЛА:
        1. ПИШИ СТРОГО НА РУССКОМ ЯЗЫКЕ!
        
        2. Учитывай предоставленный контекст:
           - Используй информацию о персонаже (пол, возраст, имя)
           - Опирайся на предыдущие события
           - Соблюдай последовательность и логику повествования
        
        3. Развивай историю в соответствии с выбором читателя:
           - Детально описывай последствия выбора
           - Создавай новые интересные ситуации
           - Поддерживай целостность повествования
        
        4. Стилистические требования:
           - Используй богатый литературный русский язык
           - Применяй разнообразные художественные приёмы
           - Соблюдай баланс между описанием и действием
        
        5. В конце предложи 3 варианта выбора:
           - Каждый выбор должен вести к разным путям развития истории
           - Варианты должны быть интригующими
           - Выборы должны учитывать характер и мотивацию героя
        
        ВАЖНО: 
        - Сначала напиши текст истории, затем отдельно варианты выбора
        - Используй ТОЛЬКО русский язык
        - Строго следуй характеристикам персонажа из контекста"""
        
        user_prompt = f"""История находится в следующем состоянии:
        {story_state}
        
        Пожалуйста, продолжи историю, учитывая все предыдущие события и последний выбор читателя."""

    logger.info(f"Story state:\n{story_state}")
    logger.info("[GENERATOR] >>> Отправляем запрос к Ollama")
    request_params = {
        "model": OLLAMA_CONFIG["model"],
        "prompt": f"System: {system_prompt}\n\nUser: {user_prompt}",
        "stream": True,
        "options": {
            "seed": OLLAMA_CONFIG["generation_params"]["seed"],
            "temperature": OLLAMA_CONFIG["generation_params"]["temperature"],
            "top_p": OLLAMA_CONFIG["generation_params"]["top_p"],
            "top_k": OLLAMA_CONFIG["generation_params"]["top_k"],
            "num_predict": OLLAMA_CONFIG["generation_params"]["num_predict"],
            "stop": OLLAMA_CONFIG["generation_params"]["stop"],
            "repeat_last_n": OLLAMA_CONFIG["generation_params"]["repeat_last_n"],
            "repeat_penalty": OLLAMA_CONFIG["generation_params"]["repeat_penalty"],
        }
    }
    logger.info(f"[GENERATOR] Параметры запроса: {json.dumps(request_params, indent=2, ensure_ascii=False)}")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{OLLAMA_CONFIG['base_url']}/api/generate",
            json=request_params
        ) as response:
            logger.info("[GENERATOR] >>> Получен ответ от Ollama, начинаем стриминг")
            story_text = ""
            buffer = ""
            current_chapter = context.get("current_chapter", 1)
            
            async for line in response.content:
                if not line.strip():
                    continue
                    
                try:
                    data = json.loads(line)
                    if "response" not in data:
                        continue
                        
                    chunk = data["response"]
                    buffer += chunk
                    
                    # Если встретили знак конца предложения, отправляем только новое предложение
                    if any(p in chunk for p in ".!?"):
                        sentence_end_idx = max(
                            buffer.rfind("."),
                            buffer.rfind("!"),
                            buffer.rfind("?")
                        )
                        
                        if sentence_end_idx > -1:
                            complete_sentence = buffer[:sentence_end_idx + 1]
                            story_text += complete_sentence + " "
                            buffer = buffer[sentence_end_idx + 1:].lstrip()
                            
                            logger.info("[GENERATOR] >>> Отправляем новое предложение")
                            # Отправляем только новое предложение
                            yield {
                                "text": story_text.strip(),
                                "choices": [],
                                "chapter": current_chapter,
                                "done": False
                            }
                            logger.info("[GENERATOR] <<< Предложение отправлено")
                    
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    logger.error(f"[GENERATOR] !!! Ошибка обработки ответа: {e}")
                    continue
            
            logger.info("[GENERATOR] >>> Стриминг завершен, обрабатываем остаток")
            # Отправляем оставшийся текст в буфере, если он есть
            if buffer:
                story_text += buffer
            
            logger.info("[GENERATOR] >>> Отправляем финальный фрагмент")
            # Сначала отправляем финальный фрагмент текста без иллюстрации
            yield {
                "text": story_text.strip() + " [DONE]",
                "choices": [],
                "chapter": current_chapter,
                "done": True
            }
            logger.info("[GENERATOR] <<< Финальный фрагмент отправлен")
            
            # Теперь генерируем промпт для иллюстрации
            illustration = None
            if story_text.strip():
                logger.info("[GENERATOR] >>> Начинаем генерацию промпта для иллюстрации")
                
                async def generate_image_prompt(text: str, max_attempts: int = 3) -> str:
                    """Генерирует промпт для изображения с проверкой на английский язык"""
                    def contains_cyrillic(text: str) -> bool:
                        return bool(re.search('[а-яА-Я]', text))
                    
                    def clean_story_text(text: str) -> str:
                        """Очищает текст от диалогов и вопросов"""
                        # Удаляем строки с цифрами и звездочками (обычно это опции выбора)
                        lines = [line for line in text.split('\n') if not re.search(r'^\d+[\.\)]|^\*+', line.strip())]
                        # Удаляем текст в кавычках (обычно это диалоги)
                        text = ' '.join(lines)
                        text = re.sub(r'"[^"]*"', '', text)
                        # Удаляем вопросительные предложения
                        text = re.sub(r'[^.!?]+\?', '', text)
                        return text.strip()
                    
                    # Очищаем текст перед генерацией
                    cleaned_text = clean_story_text(text)
                    
                    for attempt in range(max_attempts):
                        prompt_response = await session.post(
                            f"{OLLAMA_CONFIG['base_url']}/api/generate",
                            json={
                                "model": OLLAMA_CONFIG["model"],
                                "prompt": f"""Create a summary of the scene in English, focusing ONLY on visual elements and atmosphere. 
                                Include: location, lighting, main objects, and overall mood.
                                Keep it under 30 words.
                                
                                IMPORTANT: 
                                - Response must be in English only!
                                - Describe ONLY what can be seen in the scene
                                - NO dialogue or questions
                                - NO numbered lists or choices
                                
                                Story text: {cleaned_text}""",
                                "stream": False,
                                **OLLAMA_CONFIG["generation_params"]
                            }
                        )
                        
                        if prompt_response.status == 200:
                            response_text = ""
                            async for line in prompt_response.content:
                                if not line.strip():
                                    continue
                                try:
                                    data = json.loads(line)
                                    if "response" in data:
                                        response_text += data["response"]
                                except json.JSONDecodeError:
                                    continue
                            
                            response_text = response_text.strip()
                            
                            # Проверяем на наличие кириллицы
                            if not contains_cyrillic(response_text):
                                logger.info(f"[GENERATOR] Успешно сгенерирован промпт на английском (попытка {attempt + 1})")
                                return response_text
                            else:
                                logger.warning(f"[GENERATOR] Промпт содержит кириллицу, пробуем еще раз (попытка {attempt + 1})")
                                continue
                    
                    # Если все попытки неудачны, возвращаем базовый промпт
                    logger.error("[GENERATOR] Не удалось сгенерировать промпт на английском")
                    return "A mysterious scene with dark atmosphere"
                
                # Генерируем промпт с проверкой на английский
                illustration_prompt = await generate_image_prompt(story_text)
                logger.info(f"[GENERATOR] Подготовлен промпт для изображения: {illustration_prompt}")
                
                # Генерируем иллюстрацию
                illustration = await story_image_generator.generate_story_illustration({
                    'current_text': story_text,
                    'current_chapter': current_chapter,
                    'prompt': illustration_prompt,
                    'session': session  # Передаем сессию в генератор изображений
                })
                
                if illustration:
                    logger.info("[GENERATOR] >>> Отправляем сгенерированную иллюстрацию")
                    yield {
                        "type": "image",
                        "content": illustration,  # Теперь здесь base64 строка
                        "prompt": illustration_prompt
                    }
                    logger.info("[GENERATOR] <<< Иллюстрация отправлена")
            
            logger.info("[GENERATOR] <<< Генерация сегмента завершена")

async def analyze_context(text: str) -> dict:
    """Анализирует текст истории с помощью языковой модели"""
    system_prompt = """Ты - помощник для анализа текста истории. Прочитай текст и ответь на следующие вопросы:
1. Кто главный герой? Внимательно проанализируй текст и определи:
   - пол (строго ОДНО значение: "мужской" или "женский" или "-")
   - возраст (укажи "неизвестно" если не указано)
   - имя (укажи null если не названо)
2. Где происходит действие? (текущая локация)
3. Определи время:
   - время суток (утро/день/вечер/ночь)
   - сезон (зима/весна/лето/осень)
4. Что произошло? (краткое описание 2-3 ключевых событий)

Ответь в формате JSON без дополнительной разметки:
{
    "character": {
        "gender": "мужской/женский/-",
        "age": "возраст/неизвестно",
        "name": "имя или null"
    },
    "location": "где происходит действие",
    "time": {
        "day_time": "утро/день/вечер/ночь",
        "season": "зима/весна/лето/осень"
    },
    "events": ["событие 1", "событие 2"]
}

Важно: 
- Верни только JSON, без markdown-разметки и других символов
- В поле gender верни СТРОГО ОДНО значение: "мужской" или "женский" или "-"
- Определи пол по любым признакам в тексте (местоимения, окончания глаголов, описания)
- События описывай кратко, но информативно
- Если время суток или сезон не указаны явно, определи их по косвенным признакам (освещение, погода, действия персонажей)"""

    prompt = f"{system_prompt}\n\nТекст истории:\n{text}"
    
    try:
        logger.info("[CONTEXT] >>> Отправляем запрос на анализ контекста")
        response = await generate_text(prompt)
        logger.info(f"[CONTEXT] Получен ответ: {response}")
        
        # Очищаем ответ от markdown разметки
        clean_response = response.strip()
        if clean_response.startswith('```'):
            clean_response = clean_response.split('\n', 1)[1]
        if clean_response.endswith('```'):
            clean_response = clean_response.rsplit('\n', 1)[0]
        clean_response = clean_response.strip()
        
        logger.info(f"[CONTEXT] Очищенный ответ: {clean_response}")
        context = json.loads(clean_response)
        
        # Проверяем и исправляем значение пола
        if context["character"]["gender"] and "/" in context["character"]["gender"]:
            # Если модель вернула несколько значений, берем первое
            context["character"]["gender"] = context["character"]["gender"].split("/")[0]
        
        logger.info("[CONTEXT] Контекст успешно проанализирован")
        return context
    except Exception as e:
        logger.error(f"Ошибка анализа контекста: {e}")
        return {
            "character": {"gender": None, "age": None, "name": None},
            "location": "Неизвестно",
            "time": {"day_time": None, "season": None},
            "events": []
        }

async def update_story_context(text: str, choice: str, story_context: dict) -> dict:
    """Обновляет контекст истории на основе текущего текста и выбора"""
    
    # Анализируем текст с помощью модели
    context = await analyze_context(text)
    
    # Обновляем информацию о персонаже
    if context["character"]["gender"]:
        story_context["current_state"]["gender"] = context["character"]["gender"]
    if context["character"]["age"]:
        story_context["current_state"]["age"] = context["character"]["age"]
    if context["character"]["name"]:
        story_context["current_state"]["name"] = context["character"]["name"]
    
    # Обновляем локацию если она определена
    if context.get("location"):
        story_context["current_state"]["current_location"] = context["location"]
    
    # Обновляем время суток и сезон
    if context.get("time"):
        story_context["current_state"]["day_time"] = context["time"]["day_time"]
        story_context["current_state"]["season"] = context["time"]["season"]
    
    # Добавляем события в хронологию
    if context["events"]:
        # Фильтруем события, убирая дубликаты и пустые значения
        new_events = [event for event in context["events"] 
                     if event and event not in story_context["timeline"]]
        if new_events:
            story_context["timeline"].extend(new_events)
    
    # Добавляем выбор в хронологию, если он был сделан
    if choice and choice != "Начать историю":
        story_context["timeline"].append(f"Выбор: {choice}")

    # Обновляем текущее состояние
    story_context["current_state"]["current_scene"] = "Развитие истории"
    story_context["current_state"]["current_goal"] = "Продолжить приключение"

    return story_context
