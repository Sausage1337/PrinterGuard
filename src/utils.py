"""
Utility module for common dialogs and helper functions.
"""

from PySide6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QSpinBox, QDialogButtonBox, QMessageBox, QLabel
)

# --- Диалоги для работы с расходниками, пользователями, кабинетами, принтерами ---

class AddStorageDialog(QDialog):
    """Dialog for adding new items to storage."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Поступление на склад")
        self.setModal(True)
        layout = QFormLayout(self)
        self.model_edit = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["cartridge", "drum"])
        self.amount_spin = QSpinBox()
        self.amount_spin.setMinimum(1)
        self.amount_spin.setMaximum(10000)
        self.amount_spin.setValue(1)
        layout.addRow("Модель:", self.model_edit)
        layout.addRow("Тип:", self.type_combo)
        layout.addRow("Количество:", self.amount_spin)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    def get_data(self):
        """Return the entered data as a tuple (model, type, amount)."""
        return (
            self.model_edit.text().strip(),
            self.type_combo.currentText(),
            self.amount_spin.value()
        )
    def validate_data(self):
        """Validate the entered data."""
        model, _, _ = self.get_data()
        if not model:
            show_warning_message(self, "Ошибка", "Модель не может быть пустой.")
            return False
        return True

class UserDialog(QDialog):
    """Dialog for adding/editing users."""
    def __init__(self, login="", role="operator", edit_mode=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактировать пользователя" if edit_mode else "Добавить пользователя")
        self.setModal(True)
        self.edit_mode = edit_mode
        layout = QFormLayout(self)
        self.login_edit = QLineEdit(login)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.role_combo = QComboBox()
        self.role_combo.addItems(["admin", "operator", "viewer"])
        self.role_combo.setCurrentText(role)
        layout.addRow("Логин:", self.login_edit)
        if edit_mode:
            layout.addRow("Новый пароль (оставьте пустым для сохранения):", self.password_edit)
        else:
            layout.addRow("Пароль:", self.password_edit)
        layout.addRow("Роль:", self.role_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    def get_data(self):
        """Return the entered data as a tuple (login, password, role)."""
        return (
            self.login_edit.text().strip(),
            self.password_edit.text().strip(),
            self.role_combo.currentText()
        )
    def validate_data(self):
        """Validate the entered data."""
        login, password, _ = self.get_data()
        if not login:
            show_warning_message(self, "Ошибка", "Логин не может быть пустым.")
            return False
        if not self.edit_mode and not password:
            show_warning_message(self, "Ошибка", "Пароль не может быть пустым.")
            return False
        return True

class ResetPasswordDialog(QDialog):
    """Диалог для показа нового пароля после сброса."""
    def __init__(self, new_password, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Сброс пароля")
        self.setModal(True)
        layout = QFormLayout(self)
        self.info_label = QLabel(f"Новый пароль: <b>{new_password}</b>")
        layout.addRow(self.info_label)
        btns = QDialogButtonBox(QDialogButtonBox.Ok)
        btns.accepted.connect(self.accept)
        layout.addWidget(btns)

class CabinetDialog(QDialog):
    """Dialog for adding/editing cabinets."""
    def __init__(self, name="", edit_mode=False, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактировать кабинет" if edit_mode else "Добавить кабинет")
        self.setModal(True)
        layout = QFormLayout(self)
        self.name_edit = QLineEdit(name)
        layout.addRow("Название кабинета:", self.name_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    def get_data(self):
        """Return the entered cabinet name."""
        return self.name_edit.text().strip()
    def validate_data(self):
        """Validate the entered data."""
        name = self.get_data()
        if not name:
            show_warning_message(self, "Ошибка", "Название кабинета не может быть пустым.")
            return False
        return True

class PrinterDialog(QDialog):
    """Диалог для добавления/редактирования принтера."""
    def __init__(self, printer=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактировать принтер" if printer else "Добавить принтер")
        self.setModal(True)
        layout = QFormLayout(self)
        from src.database import CabinetManager
        cabinets = CabinetManager.get_all_cabinets()
        self.cabinet_combo = QComboBox()
        self.cabinet_ids = []
        for cab in cabinets:
            self.cabinet_combo.addItem(cab['name'])
            self.cabinet_ids.append(cab['id'])
        self.name_edit = QLineEdit(printer['name'] if printer else "")
        self.cartridge_edit = QLineEdit(printer['cartridge'] if printer and printer.get('cartridge') else "")
        self.drum_edit = QLineEdit(printer['drum'] if printer and printer.get('drum') else "")
        self.min_cart_spin = QSpinBox()
        self.min_cart_spin.setMinimum(0)
        self.min_cart_spin.setMaximum(1000)
        self.min_cart_spin.setValue(printer['min_cartridge_amount'] if printer and printer.get('min_cartridge_amount') else 0)
        self.min_drum_spin = QSpinBox()
        self.min_drum_spin.setMinimum(0)
        self.min_drum_spin.setMaximum(1000)
        self.min_drum_spin.setValue(printer['min_drum_amount'] if printer and printer.get('min_drum_amount') else 0)
        if printer and printer.get('cabinet_name'):
            idx = self.cabinet_combo.findText(printer['cabinet_name'])
            if idx >= 0:
                self.cabinet_combo.setCurrentIndex(idx)
        layout.addRow("Кабинет:", self.cabinet_combo)
        layout.addRow("Имя принтера:", self.name_edit)
        layout.addRow("Картридж:", self.cartridge_edit)
        layout.addRow("Драм:", self.drum_edit)
        layout.addRow("Мин. картриджей:", self.min_cart_spin)
        layout.addRow("Мин. драмов:", self.min_drum_spin)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    def get_data(self):
        return {
            'cabinet_id': self.cabinet_ids[self.cabinet_combo.currentIndex()] if self.cabinet_ids else None,
            'name': self.name_edit.text().strip(),
            'cartridge': self.cartridge_edit.text().strip(),
            'drum': self.drum_edit.text().strip(),
            'min_cartridge_amount': self.min_cart_spin.value(),
            'min_drum_amount': self.min_drum_spin.value(),
        }
    def validate_data(self):
        data = self.get_data()
        if not data['name']:
            show_warning_message(self, "Ошибка", "Имя принтера не может быть пустым.")
            return False
        return True

class WriteoffDialog(QDialog):
    """Диалог для списания расходников с принтера."""
    def __init__(self, printer_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Списание расходников: {printer_name}")
        self.setModal(True)
        layout = QFormLayout(self)
        self.cartridge_spin = QSpinBox()
        self.cartridge_spin.setMinimum(0)
        self.cartridge_spin.setMaximum(1000)
        self.cartridge_spin.setValue(0)
        self.drum_spin = QSpinBox()
        self.drum_spin.setMinimum(0)
        self.drum_spin.setMaximum(1000)
        self.drum_spin.setValue(0)
        layout.addRow("Картриджей списать:", self.cartridge_spin)
        layout.addRow("Драмов списать:", self.drum_spin)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

# --- Универсальные диалоги и утилиты ---
def show_error_message(parent, title, message):
    """Show an error message dialog."""
    QMessageBox.critical(parent, title, message)

def show_warning_message(parent, title, message):
    """Show a warning message dialog."""
    QMessageBox.warning(parent, title, message)

def show_info_message(parent, title, message):
    """Show an information message dialog."""
    QMessageBox.information(parent, title, message)

def confirm_action(parent, title, message):
    """Show a confirmation dialog and return True if accepted."""
    reply = QMessageBox.question(
        parent, title, message,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No
    )
    return reply == QMessageBox.Yes
