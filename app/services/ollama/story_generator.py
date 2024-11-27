import aiohttp
import json
import os
import re
from typing import Dict, List
from config.ollama_config import OLLAMA_CONFIG
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_next_segment(choice: str, context: Dict) -> Dict:
    # Создаем краткое описание текущего состояния истории
    story_state = "\\n".join([
        f"Текущая глава: {context['current_chapter']}",
        f"Последние выборы:",
        *[f"- {c}" for c in context['previous_choices'][-3:]],
        f"\\nТекущий выбор: {choice}"
    ])

    # Специальный промпт для первой главы
    if choice == "начало истории":
        system_prompt = """Ты - талантливый писатель, мастер художественного описания, создающий захватывающие интерактивные истории.
        Твоя задача - создать яркое, детальное и атмосферное начало истории, которое полностью погрузит читателя в мир повествования.
        
        ВАЖНЫЕ ПРАВИЛА для первой главы:
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
           - Используй богатый литературный язык
           - Применяй разнообразные художественные приёмы
           - Соблюдай баланс между описанием и действием
        
        5. В конце предложи 3 значимых варианта выбора:
           - Каждый выбор должен вести к существенно разным путям развития истории
           - Варианты должны быть интригующими и неочевидными
           - Выборы должны отражать возможные мотивации героя
        
        ВАЖНО: Сначала напиши полный текст истории, а затем отдельно в конце укажи варианты выбора."""
        
        user_prompt = """Пожалуйста, начни новую захватывающую историю. 
        Создай глубокое погружение в мир через детальное описание места действия, 
        главного героя и ситуации, в которой он оказался."""
    else:
        # Обычный промпт для продолжения истории
        system_prompt = """Ты - опытный писатель, создающий захватывающую интерактивную историю в литературном стиле.
        Твоя задача - продолжить повествование, основываясь на предыдущем контексте и выборе читателя.
        
        ВАЖНЫЕ ПРАВИЛА:
        1. ВСЕГДА начинай новый фрагмент с прямых последствий выбора читателя
        2. Сохраняй преемственность с предыдущими событиями
        3. Учитывай все предыдущие выборы при генерации нового фрагмента
        4. Не повторяй уже описанные локации и события
        5. Не игнорируй выбор читателя - он должен значимо влиять на развитие сюжета
        6. Каждый фрагмент должен быть 2-3 абзаца
        7. В конце предложи 3 варианта выбора, логически связанных с текущей ситуацией
        
        ВАЖНО: Сначала напиши полный текст продолжения, а затем отдельно в конце укажи варианты выбора."""
        
        user_prompt = f"""История находится в следующем состоянии:
        {story_state}
        
        Пожалуйста, продолжи историю, учитывая все предыдущие события и последний выбор читателя."""

    logger.info(f"Story state:\n{story_state}")
    logger.info("Sending request to Ollama with user choice and context")

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "gemma2:latest",
                "prompt": f"System: {system_prompt}\n\nUser: {user_prompt}",
                "stream": True
            }
        ) as response:
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
                    
                    # Если встретили знак конца предложения, отправляем весь буфер
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
                            
                            yield {
                                "text": story_text.strip(),
                                "choices": [],
                                "chapter": current_chapter,
                                "done": False
                            }
                    
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    logger.error(f"Error processing response: {e}")
                    continue
            
            # Отправляем оставшийся текст в буфере, если он есть
            if buffer:
                story_text += buffer
            
            # Добавляем маркер завершения в последний фрагмент
            yield {
                "text": story_text.strip() + " [DONE]",
                "choices": [],
                "chapter": current_chapter,
                "done": True
            }

    logger.info("Finished generating story segment")
