import sys
import logging
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from src.main_window import MainWindow
from src.login_dialog import LoginDialog
from src.database import init_db, UserManager

logging.basicConfig(level=logging.ERROR)

def main():
    """Main entry point for PrintGuard application."""
    try:
        init_db()
    except Exception as e:
        logging.error(f"Failed to initialize database: {e}")
        print(f"Failed to initialize database: {e}")
        return 1
    app = QApplication(sys.argv)
    while True:
        login_dialog = LoginDialog()
        if login_dialog.exec() == QDialog.Accepted:
            login, password = login_dialog.get_credentials()
            if not login or not password:
                QMessageBox.warning(None, "Ошибка", "Введите логин и пароль")
                continue
            auth_result = UserManager.authenticate(login, password)
            if auth_result:
                user_role, username = auth_result
                main_window = MainWindow(user_role=user_role, username=username)
                main_window.show()
                return app.exec()
            else:
                QMessageBox.warning(None, "Ошибка", "Неверный логин или пароль")
                continue
        else:
            break
    return 0

if __name__ == "__main__":
    sys.exit(main())
