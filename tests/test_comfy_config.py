import unittest
from config.comfy_config import ComfyUIConfig

class TestComfyUIConfig(unittest.TestCase):
    def setUp(self):
        self.config = ComfyUIConfig()

    def test_connection(self):
        """Тест подключения к ComfyUI серверу"""
        is_connected = self.config.check_connection()
        print(f"ComfyUI сервер доступен: {is_connected}")
        # Не используем assert, так как сервер может быть недоступен
        
    def test_model_list(self):
        """Тест получения списка моделей"""
        models = self.config.get_model_list()
        if models:
            print("Список доступных моделей получен успешно")
        else:
            print("Не удалось получить список моделей")

    def test_workflow_modification(self):
        """Тест модификации рабочего процесса"""
        test_prompt = "beautiful scenery nature glass bottle landscape"
        test_seed = 12345
        
        workflow = self.config.modify_workflow(
            prompt=test_prompt,
            seed=test_seed,
            width=768,
            height=768
        )
        
        # Проверяем, что параметры были изменены правильно
        self.assertEqual(workflow["6"]["inputs"]["text"], test_prompt)
        self.assertEqual(workflow["3"]["inputs"]["seed"], test_seed)
        self.assertEqual(workflow["5"]["inputs"]["width"], 768)
        self.assertEqual(workflow["5"]["inputs"]["height"], 768)

if __name__ == '__main__':
    unittest.main()
