from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import uvicorn
import json
import aiohttp
import os
import logging
from services.ollama_service import OllamaService

app = FastAPI()

# Монтируем статические файлы
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Создаем экземпляр OllamaService
ollama_service = OllamaService()

# Сохраняем контекст истории для каждого подключения
websocket_connections = {}

# Базовый роут для отображения главной страницы
@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# WebSocket для обновления истории в реальном времени
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logging.info("WebSocket connection opened")
    connection_id = str(id(websocket))
    websocket_connections[connection_id] = websocket
    
    try:
        while True:
            data = await websocket.receive_json()
            logging.info(f"Received WebSocket message: {data}")
            
            if data.get('action') == 'start_story':
                # Генерируем начало новой истории
                logging.info("Starting new story")
                story_start = await ollama_service.start_new_story()
                logging.info(f"Generated story data: {story_start}")
                
                await websocket.send_json({
                    'type': 'story_start',
                    'data': story_start
                })
            
            elif data.get('action') == 'next':
                # Генерируем следующую сцену
                selected_choice = data.get('selected_choice')
                logging.info(f"Generating next scene with choice: {selected_choice}")
                next_scene = await ollama_service.generate_next_scene(selected_choice)
                logging.info(f"Generated next scene data: {next_scene}")
                
                await websocket.send_json({
                    'type': 'story_update',
                    'data': next_scene
                })
    
    except WebSocketDisconnect:
        logging.info("WebSocket disconnected")
        if connection_id in websocket_connections:
            del websocket_connections[connection_id]
    except Exception as e:
        logging.error(f"Error in WebSocket connection: {str(e)}")
        await websocket.send_json({"error": str(e)})
        if connection_id in websocket_connections:
            del websocket_connections[connection_id]

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
