from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict
import json
import logging
from app.services.ollama import generate_next_segment

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
        # Начинаем историю
        story_context = {
            "current_chapter": 1,
            "story_state": "beginning",
            "previous_choices": []
        }
        
        # Отправляем начало истории
        initial_story = {
            "type": "story",
            "content": """Глава 1: Начало пути

Солнце медленно поднималось над горизонтом, окрашивая небо в нежные оттенки розового и золотого. Новый день нёс с собой ощущение перемен. В воздухе витало предчувствие чего-то необычного, словно сама судьба готовила неожиданный поворот в привычном течении жизни.

Утренний туман стелился по земле, окутывая подножия деревьев призрачной дымкой. В этот ранний час мир казался застывшим на грани между сном и явью, между привычным прошлым и неизведанным будущим."""
        }
        
        # Отправляем первые варианты выбора
        initial_choices = {
            "type": "choices",
            "choices": [
                "Отправиться в путь, не теряя времени",
                "Задержаться и понаблюдать за восходом",
                "Вернуться домой за забытыми вещами"
            ]
        }
        
        await websocket.send_json(initial_story)
        await websocket.send_json(initial_choices)
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "choice":
                choice = message["content"]
                story_context["previous_choices"].append(choice)
                logger.info(f"User choice received: {choice}")
                
                # Генерируем продолжение истории на основе выбора
                next_segment = await generate_next_segment(
                    choice,
                    story_context
                )
                logger.info(f"Generated story segment: {next_segment['text'][:50]}...")
                
                # Проверяем, изменилась ли глава
                if next_segment.get("chapter", story_context["current_chapter"]) > story_context["current_chapter"]:
                    # Если началась новая глава, добавляем заголовок
                    chapter_title = f"\n\nГлава {next_segment['chapter']}"
                    await websocket.send_json({
                        "type": "story",
                        "content": chapter_title
                    })
                
                # Отправляем новый фрагмент истории
                await websocket.send_json({
                    "type": "story",
                    "content": f"\n\n{next_segment['text']}"
                })
                
                # Отправляем новые варианты выбора
                await websocket.send_json({
                    "type": "choices",
                    "choices": next_segment["choices"]
                })
                
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info("WebSocket connection closed")
