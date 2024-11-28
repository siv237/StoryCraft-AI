from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict
import json
import logging
from app.services.ollama import generate_next_segment
from app.services.comfy.image_generator import story_image_generator
import aiohttp

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
                        "previous_choices": []
                    }
                else:
                    # Обычная обработка выбора
                    story_context["previous_choices"].append(choice)
                
                # Генерируем историю потоково
                current_text = ""
                async for segment in generate_next_segment(choice, story_context):
                    # Отправляем только новый текст
                    new_text = segment["text"][len(current_text):]
                    if new_text:
                        await websocket.send_json({
                            "type": "story",
                            "content": new_text,
                            "done": segment["done"]
                        })
                        current_text = segment["text"]
                    
                    # Если сегмент завершен, генерируем изображение
                    if segment["done"]:
                        # Обновляем контекст истории текущим текстом
                        story_context["current_text"] = current_text
                        
                        # Создаем сессию для генератора изображений
                        async with aiohttp.ClientSession() as session:
                            story_context["session"] = session
                            # Генерируем изображение
                            try:
                                image_path = await story_image_generator.generate_story_illustration(story_context)
                                if image_path:
                                    # Отправляем URL для просмотра изображения
                                    await websocket.send_json({
                                        "type": "image",
                                        "content": f"http://127.0.0.1:8188/view?filename={image_path}"
                                    })
                                    logger.info(f"Image sent to client: {image_path}")
                            except Exception as e:
                                logger.error(f"Error generating image: {e}")
                    
                    # Если есть варианты выбора и генерация закончена
                    if segment["choices"] and segment["done"]:
                        await websocket.send_json({
                            "type": "choices",
                            "choices": segment["choices"]
                        })
                
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info("WebSocket connection closed")
