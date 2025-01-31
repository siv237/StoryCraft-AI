import aiohttp
import json
import asyncio
from typing import Dict, Optional
import logging
from config.comfy_config import comfy_config
from config.ollama_config import OLLAMA_CONFIG, PROMPT_CONFIG
import base64
import os
import subprocess
import psutil
import time
from pathlib import Path
import uuid

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StoryImageGenerator:
    def __init__(self):
        self.comfyui_process = None
        self.comfyui_path = os.getenv('COMFYUI_PATH', '/home/user/Загрузки/Data/Packages/ComfyUI')
        
        python_path = os.getenv('COMFYUI_PYTHON_PATH', './venv/bin/python3')
        script = os.getenv('COMFYUI_SCRIPT', 'main.py')
        args = os.getenv('COMFYUI_ARGS', '--listen 0.0.0.0 --lowvram --preview-method auto --use-quad-cross-attention --force-fp32').split()
        
        self.comfyui_command = [python_path, script] + args
        logger.info(f"ComfyUI path: {self.comfyui_path}")
        logger.info(f"ComfyUI command: {self.comfyui_command}")
        
        # Формируем команду запуска из переменных окружения
        # self.comfyui_command = [
        #     './venv/bin/python3', 'main.py',
        #     '--listen', '0.0.0.0',
        #     '--lowvram',
        #     '--preview-method', 'auto',
        #     '--use-quad-cross-attention',
        #     '--force-fp32'
        # ]
        # logger.info(f"ComfyUI command: {self.comfyui_command}")

    def start_comfyui(self):
        """Запускает сервер ComfyUI"""
        logger.info("Запускаем ComfyUI сервер...")
        try:
            self.comfyui_process = subprocess.Popen(
                self.comfyui_command,
                cwd=self.comfyui_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # Увеличиваем время ожидания для CPU режима
            max_attempts = 12  # 60 секунд максимум
            for attempt in range(max_attempts):
                try:
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    result = sock.connect_ex(('127.0.0.1', 8188))
                    sock.close()
                    if result == 0:
                        logger.info("ComfyUI сервер запущен и готов к работе")
                        return
                except:
                    pass
                time.sleep(5)
                logger.info(f"Ожидаем запуск ComfyUI, попытка {attempt + 1}/{max_attempts}")
            
            logger.error("ComfyUI сервер не смог запуститься за отведенное время")
        except Exception as e:
            logger.error(f"Ошибка при запуске ComfyUI: {str(e)}")
            
    def stop_comfyui(self):
        """Останавливает сервер ComfyUI"""
        logger.info("Останавливаем ComfyUI сервер...")
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                if 'python' in proc.info['name'].lower():
                    cmdline = proc.info.get('cmdline', [])
                    if any('main.py' in cmd for cmd in cmdline) and any('--lowvram' in cmd for cmd in cmdline):
                        logger.info(f"Останавливаем процесс ComfyUI (PID: {proc.info['pid']})")
                        proc.kill()
                        proc.wait()
            logger.info("ComfyUI сервер остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке ComfyUI: {str(e)}")

    async def _translate_to_english(self, text: str, session: aiohttp.ClientSession) -> str:
        """Переводит текст на английский язык и создает краткое описание сцены"""
        max_retries = OLLAMA_CONFIG['connection']['max_retries']
        retry_delay = OLLAMA_CONFIG['connection']['retry_delay']
        
        system_prompt = """Create a very short scene description in English"""

        for attempt in range(max_retries):
            try:
                async with session.post(
                    f"{OLLAMA_CONFIG['base_url']}/api/generate",
                    json={
                        "model": OLLAMA_CONFIG['model'],
                        "system": system_prompt,
                        "prompt": text,
                        **OLLAMA_CONFIG['generation_params'],
                        "stream": True
                    }
                ) as response:
                    if response.status != 200:
                        logger.error(f"Попытка {attempt + 1}: Ошибка перевода, статус {response.status}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay * (attempt + 1))
                            continue
                        return self._fallback_translation(text)
                    
                    translation = ""
                    async for line in response.content:
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                translation += data["response"]
                        except json.JSONDecodeError:
                            continue
                    
                    return translation.strip()
                    
            except Exception as e:
                logger.error(f"Попытка {attempt + 1}: Ошибка перевода: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue
                return self._fallback_translation(text)
        
        return self._fallback_translation(text)

    def _fallback_translation(self, text: str) -> str:
        """Резервный метод перевода - простая обработка текста для генерации изображения"""
        # Возвращаем самое базовое описание
        return "character in a room, story scene"

    async def _prepare_image_prompt(self, context: Dict, session: aiohttp.ClientSession) -> str:
        """Подготавливает промпт для генерации изображения на основе контекста истории"""
        # Получаем текущий текст
        current_text = context.get('current_text', '')
        
        # Получаем краткое описание на английском
        eng_description = await self._translate_to_english(current_text, session)
        
        # Формируем промпт для изображения
        base_prompt = os.getenv("COMFYUI_BASE_PROMPT", "anime style, high quality illustration")
        prompt = f"{base_prompt}, {eng_description}"
        
        logger.info(f"Подготовлен промпт для изображения: {prompt}")
        return prompt

    async def _unload_all_models(self) -> None:
        """Выгружает все загруженные модели из GPU"""
        try:
            # Получаем список всех моделей
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{comfy_config.base_url}/object_info/CheckpointLoaderSimple") as response:
                    if response.status != 200:
                        logger.error("Не удалось получить список моделей")
                        return
                    
                    model_info = await response.json()
                    if not model_info or 'CheckpointLoaderSimple' not in model_info:
                        return
                    
                    models = model_info['CheckpointLoaderSimple']['input']['required']['ckpt_name'][0]
                    logger.info(f"Доступные модели: {', '.join(models)}")

                # Очищаем память
                async with session.post(
                    f"{comfy_config.base_url}/queue",
                    json={"clear": True}
                ) as clear_response:
                    if clear_response.status == 200:
                        logger.info("Очередь генерации очищена")
                    
                async with session.post(
                    f"{comfy_config.base_url}/free",
                    json={}
                ) as free_response:
                    if free_response.status == 200:
                        logger.info("Все модели выгружены из GPU")

        except Exception as e:
            logger.error(f"Ошибка при выгрузке моделей: {e}")

    async def _monitor_generation(self, prompt_id: str, session: aiohttp.ClientSession) -> None:
        """Мониторит процесс генерации через WebSocket"""
        client_id = f"comfyuigen_{uuid.uuid4().hex[:8]}"
        ws_url = f"ws://{comfy_config.base_url.split('://', 1)[1]}/ws?clientId={client_id}"
        
        try:
            async with session.ws_connect(ws_url) as ws:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        try:
                            data = json.loads(msg.data)
                            if not isinstance(data, dict) or 'type' not in data:
                                continue
                                
                            event_type = data['type']
                            event_data = data.get('data', {})
                            
                            # Проверяем, что событие относится к нашему prompt_id
                            if 'prompt_id' in event_data and event_data['prompt_id'] != prompt_id:
                                continue
                                
                            if event_type == "status":
                                status_data = event_data.get('status', {}).get('exec_info', {})
                                queue_remaining = status_data.get('queue_remaining', 0)
                                if queue_remaining > 0:
                                    logger.info(f"В очереди {queue_remaining} задач")
                                    
                            elif event_type == "execution_start":
                                logger.info(f"Начало генерации изображения (prompt_id: {prompt_id})")
                                
                            elif event_type == "execution_cached":
                                logger.info("Используется кэшированный результат")
                                
                            elif event_type == "executing":
                                node = event_data.get('node', 'unknown')
                                node_name = {
                                    '3': 'KSampler (генерация)',
                                    '8': 'VAE Decode (декодирование)',
                                    '9': 'SaveImage (сохранение)'
                                }.get(node, f'Node {node}')
                                logger.info(f"Выполняется {node_name}")
                                
                            elif event_type == "progress":
                                value = event_data.get('value', 0)
                                max_value = event_data.get('max', 100)
                                node = event_data.get('node', 'unknown')
                                node_name = {
                                    '3': 'KSampler',
                                    '8': 'VAE Decode',
                                    '9': 'SaveImage'
                                }.get(node, f'Node {node}')
                                logger.info(f"Прогресс {node_name}: {value}/{max_value}")
                                
                            elif event_type == "executed":
                                node = event_data.get('node', 'unknown')
                                if node == '9' and 'output' in event_data:  # SaveImage node
                                    output = event_data['output']
                                    if 'images' in output:
                                        image = output['images'][0]
                                        logger.info(f"Изображение сохранено: {image['filename']}")
                                        
                            elif event_type == "execution_error":
                                error = event_data.get('error', 'Неизвестная ошибка')
                                logger.error(f"Ошибка генерации: {error}")
                                return
                                
                            elif event_type == "execution_complete":
                                logger.info("Генерация успешно завершена")
                                return
                                
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            logger.error(f"Ошибка WebSocket мониторинга: {str(e)}")

    async def generate_story_illustration(self, context: Dict) -> Optional[str]:
        """Генерирует иллюстрацию для текущего сегмента истории"""
        try:
            self.start_comfyui()  # Запускаем ComfyUI перед генерацией
            
            session = context.get('session')
            if not session:
                # Если сессия не передана, создаем новую
                session = aiohttp.ClientSession()
                need_close = True
            else:
                need_close = False

            try:
                # Используем готовый промпт из контекста
                prompt = context.get('prompt', 'character in a room, story scene')
                base_prompt = os.getenv("COMFYUI_BASE_PROMPT", "anime style, high quality illustration")
                full_prompt = f"{base_prompt}, {prompt}"
                
                # Сначала выгружаем модель Ollama
                from app.services.ollama.story_generator import unload_model_from_gpu
                await unload_model_from_gpu()
                logger.info("Модель Ollama успешно выгружена перед генерацией изображения")

                # Теперь проверяем доступную память GPU
                async with session.get(f"{comfy_config.base_url}/system_stats") as response:
                    if response.status != 200:
                        logger.error("Не удалось получить информацию о системе")
                        return None
                    
                    stats = await response.json()
                    if 'system' in stats and 'memory' in stats['system']:
                        memory_info = stats['system']['memory']
                        free_memory = memory_info.get('free', 0)
                        total_memory = memory_info.get('total', 0)
                        
                        # Если свободной памяти меньше 2GB, пропускаем генерацию
                        if free_memory < 2 * 1024 * 1024 * 1024:  # 2GB в байтах
                            logger.warning("Недостаточно свободной памяти GPU для генерации изображения")
                            return None
                
                # Модифицируем workflow с нашим промптом
                workflow = comfy_config.modify_workflow(
                    prompt=full_prompt,
                    seed=None  # Используем случайный сид для разнообразия
                )
                
                # Отправляем запрос на генерацию
                async with session.post(
                    f"{comfy_config.base_url}/prompt",
                    json={"prompt": workflow}
                ) as response:
                    if response.status != 200:
                        logger.error(f"Ошибка запуска workflow: {await response.text()}")
                        return None
                    
                    prompt_id = (await response.json())['prompt_id']
                    logger.info(f"Запущена генерация изображения, prompt_id: {prompt_id}")
                    
                    # Запускаем мониторинг в отдельной задаче
                    monitor_task = asyncio.create_task(self._monitor_generation(prompt_id, session))
                    
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
                                            
                                            # Получаем изображение через API
                                            try:
                                                image_url = f"{comfy_config.base_url}/view?filename={image_path}"
                                                async with session.get(image_url) as response:
                                                    if response.status == 200:
                                                        img_data = await response.read()
                                                        base64_img = base64.b64encode(img_data).decode('utf-8')
                                                        return f"data:image/png;base64,{base64_img}"
                                                    else:
                                                        logger.error(f"Ошибка при получении изображения: {response.status}")
                                                        return None
                                            except Exception as e:
                                                logger.error(f"Ошибка при получении изображения: {e}")
                                                return None
                                    break
                            
                        await asyncio.sleep(1)  # Пауза между проверками
                        
            finally:
                if need_close:
                    await session.close()
                    
        except Exception as e:
            logger.error(f"Ошибка генерации иллюстрации: {e}")
            return None
        finally:
            self.stop_comfyui()  # Останавливаем ComfyUI после генерации

# Создаем экземпляр генератора изображений
story_image_generator = StoryImageGenerator()
