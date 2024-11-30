let ws = null;
let currentStory = null;
let isGenerating = false;  // Флаг для предотвращения множественных запросов

// Инициализация WebSocket соединения
function initWebSocket() {
    console.log('Initializing WebSocket...');
    ws = new WebSocket(`ws://${window.location.host}/ws`);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
        document.getElementById('start-btn').disabled = false;
        document.getElementById('next-btn').disabled = true;
    };
    
    ws.onmessage = (event) => {
        console.log('Received message:', event.data);
        try {
            const data = JSON.parse(event.data);
            console.log('Parsed data:', data);
            
            if (data.type === 'story_start') {
                handleStoryStart(data.data);
            } else if (data.type === 'story_update') {
                handleStoryUpdate(data.data);
            } else if (data.type === 'context') {
                updateContext(data.content);
            } else if (data.error) {
                console.error('Error from server:', data.error);
                showError(data.error);
            }
        } catch (error) {
            console.error('Error handling message:', error);
            showError('Ошибка при обработке сообщения');
        }
    };
    
    ws.onclose = () => {
        console.log('WebSocket disconnected');
        document.getElementById('start-btn').disabled = true;
        document.getElementById('next-btn').disabled = true;
        setTimeout(initWebSocket, 5000);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        showError('Ошибка соединения');
    };
}

// Обработка начала истории
function handleStoryStart(data) {
    console.log('Handling story start:', data);
    
    // Очищаем предыдущий текст и кнопки
    clearDialogText();
    hideChoices();
    
    // Очищаем окно развития сюжета
    const storyProgress = document.getElementById('story-progress');
    storyProgress.innerHTML = '<h2>Развитие сюжета</h2>';
    
    // Добавляем событие начала истории
    addStoryEvent('scene', 'История началась');
    
    // Обновляем сцену
    updateScene(data);
    
    // Активируем кнопку "Далее" и деактивируем "Начать"
    document.getElementById('next-btn').disabled = false;
    document.getElementById('start-btn').disabled = true;
}

// Обработка обновления истории
function handleStoryUpdate(data) {
    console.log('Handling story update:', data);
    
    // Очищаем предыдущий текст и кнопки
    clearDialogText();
    hideChoices();
    
    // Добавляем новые события в окно развития сюжета
    if (data.scene_description) {
        addStoryEvent('scene', data.scene_description);
    }
    if (data.dialog) {
        addStoryEvent('dialog', `${data.character_name}: ${data.dialog}`);
    }
    
    // Обновляем сцену
    updateScene(data);
}

// Обновление сцены
async function updateScene(data) {
    console.log('Updating scene with data:', data);
    
    // Обновляем имя персонажа
    const characterName = document.getElementById('character-name');
    if (data.character_name) {
        characterName.textContent = data.character_name;
        characterName.style.display = 'block';
    } else {
        characterName.style.display = 'none';
    }
    
    // Составляем текст для отображения
    let fullText = '';
    if (data.scene_description) {
        fullText += data.scene_description + '\n\n';
    }
    if (data.dialog) {
        fullText += data.dialog;
    }
    
    // Отображаем текст
    if (fullText) {
        const dialogText = document.getElementById('dialog-text');
        await typeWriter(dialogText, fullText);
    }
    
    // Показываем варианты выбора или кнопку "Далее"
    if (data.choices && data.choices.length > 0) {
        showChoices(data.choices);
        document.getElementById('next-btn').style.display = 'none';
    } else {
        document.getElementById('next-btn').style.display = 'block';
        hideChoices();
    }
}

// Обработка нажатия кнопки "Далее"
function handleNextButton() {
    console.log('Next button clicked');
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ action: 'next' }));
    } else {
        showError('Соединение потеряно. Обновите страницу.');
    }
}

// Обработка выбора варианта
function handleChoice(choiceText) {
    console.log('Selected choice:', choiceText);
    
    // Добавляем выбор в окно развития сюжета
    addStoryEvent('choice', `Выбор: ${choiceText}`);
    
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            action: 'next',
            selected_choice: choiceText
        }));
    } else {
        showError('Соединение потеряно. Обновите страницу.');
    }
}

// Обновление контекста истории
function updateContext(data) {
    console.log('Updating context:', data);
    
    // Обновляем информацию о персонаже
    if (data.character) {
        document.getElementById('character-gender').textContent = data.character.gender || '-';
        document.getElementById('character-age').textContent = data.character.age || 'неизвестно';
        document.getElementById('character-name').textContent = data.character.name || '-';
    }
    
    // Обновляем события
    if (data.timeline) {
        const timelineElement = document.getElementById('timeline');
        timelineElement.innerHTML = '';
        data.timeline.forEach(event => {
            const li = document.createElement('li');
            li.textContent = event;
            timelineElement.appendChild(li);
        });
    }
    
    // Обновляем текущее состояние
    if (data.current_state) {
        document.getElementById('current-location').textContent = 
            data.current_state.current_location || 'Неизвестно';
        document.getElementById('current-scene').textContent = 
            data.current_state.current_scene || 'Информация обновляется...';
        document.getElementById('current-goal').textContent = 
            data.current_state.current_goal || 'Информация обновляется...';
    }
}

// Функции для работы с окном развития сюжета
function addStoryEvent(type, content) {
    const storyProgress = document.getElementById('story-progress');
    const eventElement = document.createElement('div');
    eventElement.className = `story-event ${type}`;
    
    const timeElement = document.createElement('div');
    timeElement.className = 'story-event-time';
    timeElement.textContent = new Date().toLocaleTimeString();
    
    const contentElement = document.createElement('div');
    contentElement.className = 'story-event-content';
    contentElement.textContent = content;
    
    eventElement.appendChild(timeElement);
    eventElement.appendChild(contentElement);
    storyProgress.appendChild(eventElement);
    
    // Прокручиваем к новому событию
    eventElement.scrollIntoView({ behavior: 'smooth', block: 'end' });
}

// Эффект печатания текста
async function typeWriter(element, text, speed = 50) {
    console.log('Starting typeWriter with text:', text);
    element.textContent = '';
    
    const lines = text.split('\n');
    for (let i = 0; i < lines.length; i++) {
        if (i > 0) {
            element.appendChild(document.createElement('br'));
        }
        const line = lines[i];
        for (let j = 0; j < line.length; j++) {
            element.textContent += line[j];
            await new Promise(resolve => setTimeout(resolve, speed));
        }
    }
    console.log('Finished typeWriter');
}

// Вспомогательные функции
function clearDialogText() {
    const dialogText = document.getElementById('dialog-text');
    dialogText.textContent = '';
}

function hideChoices() {
    const choicesContainer = document.querySelector('.choices-container');
    choicesContainer.style.display = 'none';
}

function showChoices(choices) {
    console.log('Showing choices:', choices);
    const choicesContainer = document.querySelector('.choices-container');
    choicesContainer.innerHTML = '';
    
    choices.forEach(choice => {
        const button = document.createElement('button');
        button.className = 'choice-btn';
        button.textContent = choice.text;
        button.onclick = () => handleChoice(choice.text);
        choicesContainer.appendChild(button);
    });
    
    choicesContainer.style.display = 'flex';
}

function showError(message) {
    console.error(message);
    const errorElement = document.getElementById('error-message');
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.style.display = 'block';
        setTimeout(() => {
            errorElement.style.display = 'none';
        }, 5000);
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    console.log('Page loaded, initializing...');
    initWebSocket();
    
    // Обработчик для кнопки "Начать"
    const startBtn = document.getElementById('start-btn');
    if (startBtn) {
        startBtn.onclick = () => {
            console.log('Start button clicked');
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ action: 'start_story' }));
            } else {
                showError('Нет соединения с сервером');
            }
        };
    }
    
    // Обработчик для кнопки "Далее"
    const nextBtn = document.getElementById('next-btn');
    if (nextBtn) {
        nextBtn.onclick = handleNextButton;
    }
});
