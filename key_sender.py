import time
import threading
from typing import List, Union
from pynput import keyboard
from pynput.keyboard import Key, Listener
import logging

logger = logging.getLogger(__name__)

class KeySender:
    def __init__(self):
        self.controller = keyboard.Controller()
        self.is_active = False
        
    def send_text(self, text: str, delay: float = 0.05) -> bool:
        """Отправить текст с задержкой между символами."""
        try:
            for char in text:
                if not self.is_active:
                    return False
                self.controller.type(char)
                time.sleep(delay)
            return True
        except Exception as e:
            logger.error(f"Ошибка при отправке текста: {e}")
            return False
    
    def send_key(self, key: Union[str, Key], delay: float = 0.1) -> bool:
        """Отправить одиночную клавишу."""
        try:
            if isinstance(key, str):
                # Специальные клавиши
                key_map = {
                    'enter': Key.enter,
                    'tab': Key.tab,
                    'space': Key.space,
                    'backspace': Key.backspace,
                    'delete': Key.delete,
                    'escape': Key.esc,
                    'ctrl': Key.ctrl,
                    'alt': Key.alt,
                    'shift': Key.shift,
                    'win': Key.cmd,  # Windows key
                    'up': Key.up,
                    'down': Key.down,
                    'left': Key.left,
                    'right': Key.right,
                    'home': Key.home,
                    'end': Key.end,
                    'page_up': Key.page_up,
                    'page_down': Key.page_down,
                    'f1': Key.f1, 'f2': Key.f2, 'f3': Key.f3, 'f4': Key.f4,
                    'f5': Key.f5, 'f6': Key.f6, 'f7': Key.f7, 'f8': Key.f8,
                    'f9': Key.f9, 'f10': Key.f10, 'f11': Key.f11, 'f12': Key.f12,
                }
                key = key_map.get(key.lower(), key)
            
            self.controller.press(key)
            time.sleep(delay)
            self.controller.release(key)
            return True
        except Exception as e:
            logger.error(f"Ошибка при отправке клавиши: {e}")
            return False
    
    def send_hotkey(self, *keys: Union[str, Key], delay: float = 0.1) -> bool:
        """Отправить комбинацию клавиш (Ctrl+C, Alt+Tab и т.д.)."""
        try:
            # Нажимаем все клавиши одновременно
            for key in keys:
                if isinstance(key, str):
                    key_map = {
                        'ctrl': Key.ctrl, 'alt': Key.alt, 'shift': Key.shift,
                        'win': Key.cmd, 'enter': Key.enter, 'tab': Key.tab,
                        'space': Key.space, 'escape': Key.esc,
                    }
                    key = key_map.get(key.lower(), key)
                self.controller.press(key)
            
            time.sleep(delay)
            
            # Отпускаем все клавиши в обратном порядке
            for key in reversed(keys):
                if isinstance(key, str):
                    key_map = {
                        'ctrl': Key.ctrl, 'alt': Key.alt, 'shift': Key.shift,
                        'win': Key.cmd, 'enter': Key.enter, 'tab': Key.tab,
                        'space': Key.space, 'escape': Key.esc,
                    }
                    key = key_map.get(key.lower(), key)
                self.controller.release(key)
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при отправке комбинации: {e}")
            return False
    
    def send_sequence(self, sequence: List[Union[str, Key]], delay: float = 0.1) -> bool:
        """Отправить последовательность клавиш."""
        try:
            for key in sequence:
                if not self.is_active:
                    return False
                self.send_key(key, delay)
                time.sleep(delay)
            return True
        except Exception as e:
            logger.error(f"Ошибка при отправке последовательности: {e}")
            return False
    
    def start_sending(self):
        """Активировать отправку клавиш."""
        self.is_active = True
    
    def stop_sending(self):
        """Деактивировать отправку клавиш."""
        self.is_active = False
    
    def is_running(self) -> bool:
        """Проверить, активна ли отправка клавиш."""
        return self.is_active


# Предустановленные команды
PRESET_COMMANDS = {
    "notepad": ["win", "r", "notepad", "enter"],
    "calculator": ["win", "r", "calc", "enter"],
    "task_manager": ["ctrl", "shift", "escape"],
    "desktop": ["win", "d"],
    "alt_tab": ["alt", "tab"],
    "copy": ["ctrl", "c"],
    "paste": ["ctrl", "v"],
    "cut": ["ctrl", "x"],
    "select_all": ["ctrl", "a"],
    "save": ["ctrl", "s"],
    "new_window": ["ctrl", "n"],
    "close_window": ["alt", "f4"],
    "refresh": ["f5"],
    "search": ["ctrl", "f"],
    "fullscreen": ["f11"],
    "screenshot": ["win", "shift", "s"],
    "lock_screen": ["win", "l"],
    "shutdown": ["win", "x", "u", "u"],  # Win+X, U, U для выключения
    "restart": ["win", "x", "u", "r"],   # Win+X, U, R для перезагрузки
    "sleep": ["win", "x", "u", "s"],    # Win+X, U, S для сна
}


# Глобальный экземпляр
key_sender = KeySender()
