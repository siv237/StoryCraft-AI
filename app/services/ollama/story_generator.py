import aiohttp
import json
import os
from typing import Dict, List
from config.ollama_config import OLLAMA_CONFIG
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_next_segment(choice: str, context: Dict) -> Dict:
    system_prompt = """Ты - опытный писатель, создающий захватывающую интерактивную историю в литературном стиле.
    Твоя задача - продолжить повествование, основываясь на предыдущем контексте и выборе читателя.
    
    ВАЖНЫЕ ПРАВИЛА:
    1. ВСЕГДА начинай новый фрагмент с прямых последствий выбора читателя
    2. Сохраняй преемственность с предыдущими событиями
    3. Учитывай все предыдущие выборы при генерации нового фрагмента
    4. Не повторяй уже описанные локации и события
    5. Не игнорируй выбор читателя - он должен значимо влиять на развитие сюжета
    6. Каждый фрагмент должен быть 2-3 абзаца
    7. Предлагай 3 варианта выбора, логически связанных с текущей ситуацией
    
    Пример хорошего продолжения:
    Выбор: "Исследовать тёмный коридор"
    Продолжение: "Собравшись с духом, путник шагнул в темноту коридора. Его шаги гулко отдавались от каменных стен, а впереди мерцал слабый свет..."
    
    Формат ответа должен быть в JSON:
    {
        "text": "продолжение истории",
        "choices": ["вариант 1", "вариант 2", "вариант 3"],
        "chapter": номер_текущей_главы
    }"""

    # Создаем краткое описание текущего состояния истории
    story_state = "\\n".join([
        f"Текущая глава: {context['current_chapter']}",
        f"Последние выборы:",
        *[f"- {choice}" for choice in context['previous_choices'][-3:]],
        f"\\nТекущий выбор: {choice}"
    ])

    user_prompt = f"""История находится в следующем состоянии:
    {story_state}
    
    Пожалуйста, продолжи историю, учитывая все предыдущие события и последний выбор читателя.
    ВАЖНО: Новый фрагмент должен быть прямым следствием выбора читателя и логически связан с предыдущими событиями."""

    logger.info(f"Story state:\n{story_state}")
    logger.info("Sending request to Ollama with user choice and context")

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{OLLAMA_CONFIG['base_url']}/api/generate",
            json={
                "model": OLLAMA_CONFIG["model"],
                "system": system_prompt,
                "prompt": user_prompt,
                "stream": False,
                "options": OLLAMA_CONFIG["generation_params"]
            }
        ) as response:
            logger.info("Received response from Ollama")
            result = await response.json()
            logger.info(f"Raw response from Ollama: {result}")
            try:
                # Удаляем тройные обратные кавычки из начала и конца
                raw_text = result["response"]
                # Находим начало и конец JSON
                json_start = raw_text.find('{')
                json_end = raw_text.rfind('}') + 1
                if json_start == -1 or json_end == 0:
                    raise ValueError("JSON markers not found in response")
                
                json_response = raw_text[json_start:json_end]
                logger.info(f"Extracted JSON string: {json_response}")
                response_data = json.loads(json_response)
                
                # Обновляем состояние истории
                if len(context['previous_choices']) % 3 == 0:
                    context['current_chapter'] += 1
                
                return {
                    "text": response_data["text"],
                    "choices": response_data["choices"],
                    "chapter": context["current_chapter"]
                }
            except json.JSONDecodeError:
                logger.error("Failed to parse response from Ollama")
                # Если что-то пошло не так, возвращаем базовый ответ
                return {
                    "text": "История на мгновение замерла, словно задумавшись о следующем повороте сюжета...",
                    "choices": [
                        "Продолжить путь",
                        "Осмотреться вокруг",
                        "Сделать паузу и подумать"
                    ],
                    "chapter": context["current_chapter"]
                }
