from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox


class LoginDialog(QDialog):
    """Диалог для входа пользователя."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Вход")
        layout = QFormLayout(self)
        self.login_edit = QLineEdit()
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.Password)
        layout.addRow("Логин:", self.login_edit)
        layout.addRow("Пароль:", self.pass_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_credentials(self):
        """Получить введённые пользователем логин и пароль."""
        return self.login_edit.text(), self.pass_edit.text()

