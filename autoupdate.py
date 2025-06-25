import sys
import os
import requests
import zipfile
import io
import logging

GITHUB_REPO = "Sausage1337/printersbux"  # Замените на свой репозиторий, если нужно
APP_FILENAME = "BotPrinters.exe"
VERSION = "1.0.0"  # Меняйте при каждом релизе

logging.basicConfig(level=logging.ERROR)

def get_latest_release():
    """Получить информацию о последнем релизе с GitHub."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

def check_new_version():
    """Проверить, есть ли новая версия приложения."""
    rel = get_latest_release()
    latest_version = rel["tag_name"]
    if latest_version > VERSION:
        return rel
    return None

def download_and_replace(rel, parent_widget=None):
    """Скачать и заменить файлы приложения из релиза."""
    asset = next((a for a in rel["assets"] if a["name"].endswith(".zip")), None)
    if not asset:
        if parent_widget:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(parent_widget, "Обновление", "В релизе нет zip-архива!")
        return False
    try:
        r = requests.get(asset["browser_download_url"])
        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall(".")
        return True
    except Exception as e:
        logging.error(f"Ошибка при загрузке и распаковке обновления: {e}")
        if parent_widget:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(parent_widget, "Обновление", f"Ошибка загрузки: {e}")
        return False

def restart():
    """Перезапустить приложение."""
    if sys.platform == "win32":
        os.execv(sys.executable, [sys.executable] + sys.argv)
    else:
        os.execl(sys.executable, sys.executable, *sys.argv)

def check_and_update_gui(parent_widget=None):
    """Проверить обновления и запустить процесс обновления через GUI."""
    from PySide6.QtWidgets import QMessageBox
    try:
        rel = check_new_version()
    except Exception as e:
        logging.error(f"Ошибка проверки обновления: {e}")
        QMessageBox.critical(parent_widget, "Ошибка обновления", f"Ошибка проверки обновления:\n{e}")
        return
    if rel:
        res = QMessageBox.question(
            parent_widget,
            "Обновление",
            f"Найдена новая версия: {rel['tag_name']}\nОбновить сейчас?",
            QMessageBox.Yes | QMessageBox.No
        )
        if res == QMessageBox.Yes:
            ok = download_and_replace(rel, parent_widget)
            if ok:
                QMessageBox.information(parent_widget, "Обновление", "Обновление установлено. Приложение будет перезапущено.")
                restart()
            else:
                QMessageBox.critical(parent_widget, "Обновление", "Обновление не удалось.")
    else:
        QMessageBox.information(parent_widget, "Обновление", "У вас уже последняя версия.")