from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import logging
from app.services.ollama import generate_next_segment
from app.services.comfy.image_generator import story_image_generator
from app.services.ollama.story_generator import update_story_context
import aiohttp
import asyncio
import json
from config.ollama_config import OLLAMA_CONFIG

router = APIRouter()
active_connections: List[WebSocket] = []

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    logger.info("WebSocket connection accepted")
    
    try:
        # Начинаем с кнопки "Начать историю"
        await websocket.send_json({
            "type": "choices",
            "choices": ["Начать историю"]
        })
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "choice":
                choice = message["content"]
                logger.info(f"User choice received: {choice}")
                
                if choice == "Начать историю":
                    # Инициализируем контекст истории
                    story_context = {
                        "current_chapter": 1,
                        "story_state": "beginning",
                        "previous_choices": [],
                        "characters": [],
                        "timeline": ["История еще не началась..."],
                        "current_state": {
                            "location": "Неизвестно",
                            "scene": "Ожидание начала истории",
                            "goal": "Начать приключение"
                        }
                    }
                else:
                    # Обычная обработка выбора
                    story_context["previous_choices"].append(choice)
                
                # Генерируем историю потоково
                current_text = ""
                async for segment in generate_next_segment(choice, story_context):
                    # Если это сообщение с картинкой, просто пересылаем его
                    if "type" in segment and segment["type"] == "image":
                        logger.info("[STORY] >>> Пересылаем картинку клиенту")
                        await websocket.send_json(segment)
                        logger.info("[STORY] <<< Картинка отправлена")
                        continue

                    # Отправляем только новый текст
                    new_text = segment["text"][len(current_text):]
                    if new_text:
                        logger.info("[STORY] >>> Начинаем отправку нового текста клиенту")
                        await websocket.send_json({
                            "type": "story",
                            "content": new_text,
                            "done": segment["done"]
                        })
                        logger.info("[STORY] <<< Текст отправлен клиенту")
                        current_text = segment["text"]
                        logger.info(f"[STORY] Текущий текст обновлен, done={segment['done']}")

                        # Если это финальный фрагмент, обновляем контекст
                        if segment["done"]:
                            logger.info("[STORY] >>> Обновляем контекст истории")
                            # Обновляем контекст на основе текста
                            story_context = await update_story_context(current_text, choice, story_context)
                            # Отправляем обновленный контекст клиенту
                            await websocket.send_json({
                                "type": "context",
                                "content": {
                                    "characters": story_context.get("characters", []),
                                    "timeline": story_context.get("timeline", []),
                                    "current_state": story_context.get("current_state", {})
                                }
                            })
                            logger.info("[STORY] <<< Контекст обновлен и отправлен")
                    
                    # Когда история завершена и есть варианты выбора
                    if segment["choices"] and segment["done"]:
                        logger.info("[STORY] >>> Начинаем обработку завершенного сегмента")
                        logger.info(f"[STORY] Варианты выбора: {segment['choices']}")
                        
                        logger.info("=== ЗАВЕРШЕНО ПОЛУЧЕНИЕ ДАННЫХ ОТ OLLAMA ===")
                        logger.info(f"Текущий текст: {current_text}")
                        logger.info(f"Варианты выбора: {segment['choices']}")
                        
                        logger.info("[STORY] >>> Отправляем варианты выбора")
                        await websocket.send_json({
                            "type": "choices",
                            "choices": segment["choices"]
                        })
                        logger.info("[STORY] <<< Варианты выбора отправлены")
                        logger.info("=== КНОПКИ ОТПРАВЛЕНЫ, НАЧИНАЕМ 5-СЕКУНДНОЕ ОЖИДАНИЕ ===")
                        
                        # Ждем 5 секунд, чтобы пользователь мог сделать выбор
                        try:
                            logger.info("Ждем 5 секунд на выбор пользователя")
                            await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                            logger.info("Пользователь сделал выбор, пропускаем генерацию картинки")
                            continue
                        except asyncio.TimeoutError:
                            logger.info("Пользователь не сделал выбор за 5 секунд")
                            
                            # Только теперь начинаем генерацию промпта и картинки
                            story_context["current_text"] = current_text
                            async with aiohttp.ClientSession() as session:
                                story_context["session"] = session
                                
                                try:
                                    # 1. Генерируем английский промпт
                                    logger.info("Начинаем генерацию промпта для изображения")
                                    prompt = await story_image_generator._translate_to_english(current_text, session)
                                    logger.info(f"Сгенерирован промпт: {prompt}")
                                    
                                    # 2. Выгружаем Ollama
                                    logger.info("Выгрузка модели Ollama")
                                    async with session.post(
                                        f"{OLLAMA_CONFIG['base_url']}/api/generate",
                                        json={
                                            "model": OLLAMA_CONFIG['model'],
                                            "prompt": "",
                                            "keep_alive": 0
                                        }
                                    ) as response:
                                        if response.status == 200:
                                            logger.info("Модель Ollama успешно выгружена")
                                    
                                    # 3. Генерируем изображение
                                    logger.info("Начинаем генерацию изображения")
                                    story_context["prompt"] = prompt  # Передаем готовый промпт
                                    image_path = await story_image_generator.generate_story_illustration(story_context)
                                    
                                    if image_path:
                                        logger.info(f"Изображение сгенерировано: {image_path}")
                                        await websocket.send_json({
                                            "type": "image",
                                            "content": f"http://127.0.0.1:8188/view?filename={image_path}",
                                            "prompt": prompt
                                        })
                                        logger.info("Изображение отправлено клиенту")
                                except Exception as e:
                                    logger.error(f"Ошибка при генерации изображения: {e}")
                
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info("WebSocket connection closed")
