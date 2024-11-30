from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Character:
    name: str
    gender: Optional[str] = None
    age: Optional[str] = None
    description: Optional[str] = None
    traits: List[str] = field(default_factory=list)
    relationships: Dict[str, str] = field(default_factory=dict)

@dataclass
class TimelineEvent:
    timestamp: datetime
    description: str
    characters: List[str]
    location: Optional[str] = None

class StoryContext:
    def __init__(self):
        self.characters: Dict[str, Character] = {}
        self.timeline: List[TimelineEvent] = []
        self.current_state: Dict[str, str] = {
            "current_location": None,
            "current_scene": None,
            "current_goal": None
        }
        
    def add_character(self, name: str, gender: Optional[str] = None, 
                     age: Optional[str] = None, description: Optional[str] = None) -> None:
        """Добавляет нового персонажа или обновляет существующего"""
        if name not in self.characters:
            self.characters[name] = Character(name=name, gender=gender, 
                                           age=age, description=description)
        else:
            char = self.characters[name]
            if gender: char.gender = gender
            if age: char.age = age
            if description: char.description = description

    def add_character_trait(self, character_name: str, trait: str) -> None:
        """Добавляет черту характера персонажу"""
        if character_name in self.characters and trait not in self.characters[character_name].traits:
            self.characters[character_name].traits.append(trait)

    def add_relationship(self, character1: str, character2: str, relationship: str) -> None:
        """Добавляет отношения между персонажами"""
        if character1 in self.characters and character2 in self.characters:
            self.characters[character1].relationships[character2] = relationship
            # Добавляем обратное отношение, если это имеет смысл
            # Например: если А - отец B, то B - ребёнок A
            # Это можно будет доработать позже

    def add_event(self, description: str, characters: List[str], location: Optional[str] = None) -> None:
        """Добавляет новое событие в хронологию"""
        event = TimelineEvent(
            timestamp=datetime.now(),
            description=description,
            characters=characters,
            location=location
        )
        self.timeline.append(event)

    def update_current_state(self, location: Optional[str] = None, 
                           scene: Optional[str] = None, 
                           goal: Optional[str] = None) -> None:
        """Обновляет текущее состояние истории"""
        if location: self.current_state["current_location"] = location
        if scene: self.current_state["current_scene"] = scene
        if goal: self.current_state["current_goal"] = goal

    def get_context_display(self) -> Dict:
        """Возвращает контекст в формате для отображения"""
        characters_display = []
        for char in self.characters.values():
            char_info = f"{char.name}"
            if char.gender or char.age:
                details = []
                if char.gender: details.append(char.gender)
                if char.age: details.append(char.age)
                char_info += f" ({', '.join(details)})"
            if char.description:
                char_info += f"\n  {char.description}"
            if char.traits:
                char_info += f"\n  Черты: {', '.join(char.traits)}"
            if char.relationships:
                rels = [f"{k}: {v}" for k, v in char.relationships.items()]
                char_info += f"\n  Отношения: {', '.join(rels)}"
            characters_display.append(char_info)

        timeline_display = []
        for event in self.timeline:
            event_info = f"• {event.description}"
            if event.location:
                event_info += f" (Место: {event.location})"
            timeline_display.append(event_info)

        return {
            "characters": characters_display,
            "timeline": timeline_display,
            "current_state": {
                "Текущая локация": self.current_state["current_location"],
                "Текущая сцена": self.current_state["current_scene"],
                "Текущая цель": self.current_state["current_goal"]
            }
        }
