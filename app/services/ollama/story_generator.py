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
                "http://localhost:11434/api/generate",
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

async def generate_next_segment(choice: str, context: Dict) -> Dict:
    # Сначала выгружаем модели ComfyUI чтобы освободить память для Ollama
    await story_image_generator._unload_all_models()

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
                            
                            # Отправляем только новое предложение
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
            
            # Генерируем промпт для иллюстрации
            illustration = None
            if story_text.strip():
                # Используем ту же сессию Ollama для подготовки промпта и перевода
                prompt_response = await session.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": OLLAMA_CONFIG["model"],
                        "prompt": f"""Create a detailed image generation prompt in English for this story segment. 
                        Focus on the main scene, mood, and key visual elements. Format: 'book illustration, detailed artistic scene, 
                        high quality, masterpiece,' followed by the specific scene description.
                        
                        Story segment: {story_text}""",
                        "stream": True
                    }
                )
                
                if prompt_response.status == 200:
                    illustration_prompt = ""
                    async for line in prompt_response.content:
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                illustration_prompt += data["response"]
                        except json.JSONDecodeError:
                            continue
                    
                    logger.info(f"Подготовлен промпт для изображения: {illustration_prompt}")
                
                    # Генерируем иллюстрацию
                    illustration = await story_image_generator.generate_story_illustration({
                        'current_text': story_text,
                        'current_chapter': current_chapter,
                        'prompt': illustration_prompt,
                        'session': session  # Передаем сессию в генератор изображений
                    })
            
            # Добавляем маркер завершения и иллюстрацию в последний фрагмент
            yield {
                "text": story_text.strip() + " [DONE]",
                "choices": [],
                "chapter": current_chapter,
                "done": True,
                "illustration": illustration
            }

    logger.info("Finished generating story segment")
