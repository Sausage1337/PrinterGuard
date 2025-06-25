import sys
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QTabWidget, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QFormLayout, QLineEdit,
    QSpinBox, QDialogButtonBox, QComboBox, QDialog, QTextEdit
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from src.database import PrinterManager, StorageManager, UserManager, CabinetManager
from src.utils import CabinetDialog, PrinterDialog, WriteoffDialog, UserDialog, ResetPasswordDialog
from analytics import (
    get_cartridge_usage_by_month, get_top5_cartridge_models, get_cartridge_forecast,
    get_cartridge_change_report, plot_cartridge_usage, export_cartridge_usage_to_excel
)
try:
    import autoupdate
except Exception as e:
    autoupdate = None
    import traceback
    def show_update_error(parent):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(parent, "Ошибка обновления", f"Ошибка импорта autoupdate:\n{traceback.format_exc()}")

# --- Константы для индексов столбцов ---
STORAGE_COL_MODEL = 0
STORAGE_COL_TYPE = 1
STORAGE_COL_AMOUNT = 2

class MainWindow(QMainWindow):
    """Главное окно приложения учёта принтеров и расходников."""
    def __init__(self, user_role, username, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PrintGuard — учёт принтеров и расходников")
        self.resize(1280, 750)
        self.user_role = user_role
        self.username = username
        self._init_ui()

    def _init_ui(self):
        """Инициализация интерфейса пользователя."""
        self._init_menu()
        self._init_tabs()
        self._init_layout()
        self._connect_menu()
        self._apply_role_restrictions()
        self._fill_tabs()

    def _init_menu(self):
        self.menu_widget = QWidget()
        menu_layout = QVBoxLayout(self.menu_widget)
        menu_layout.setSpacing(12)
        self.btn_overview = QPushButton("Обзор")
        self.btn_cabinets = QPushButton("Кабинеты")
        self.btn_printers = QPushButton("Принтеры")
        self.btn_storage = QPushButton("Склад")
        self.btn_history = QPushButton("История")
        self.btn_analytics = QPushButton("Аналитика")
        self.btn_users = QPushButton("Пользователи")
        self.btn_update = QPushButton("Обновление")
        self.btn_exit = QPushButton("Выход")
        for btn in [
            self.btn_overview, self.btn_cabinets, self.btn_printers, self.btn_storage,
            self.btn_history, self.btn_analytics, self.btn_users, self.btn_update, self.btn_exit]:
            btn.setMinimumHeight(36)
            menu_layout.addWidget(btn)
        menu_layout.addStretch(1)

    def _init_tabs(self):
        self.tabs = QTabWidget()
        self.tab_overview = QWidget()
        self.tab_cabinets = QWidget()
        self.tab_printers = QWidget()
        self.tab_storage = QWidget()
        self.tab_history = QWidget()
        self.tab_analytics = QWidget()
        self.tab_users = QWidget()
        self.tabs.addTab(self.tab_overview, "Обзор")
        self.tabs.addTab(self.tab_cabinets, "Кабинеты")
        self.tabs.addTab(self.tab_printers, "Принтеры")
        self.tabs.addTab(self.tab_storage, "Склад")
        self.tabs.addTab(self.tab_history, "История")
        self.tabs.addTab(self.tab_analytics, "Аналитика")
        self.tabs.addTab(self.tab_users, "Пользователи")

    def _init_layout(self):
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        main_layout.addWidget(self.menu_widget, 0)
        main_layout.addWidget(self.tabs, 1)
        self.setCentralWidget(central_widget)

    def _connect_menu(self):
        self.btn_overview.clicked.connect(lambda: self.tabs.setCurrentWidget(self.tab_overview))
        self.btn_cabinets.clicked.connect(lambda: self.tabs.setCurrentWidget(self.tab_cabinets))
        self.btn_printers.clicked.connect(lambda: self.tabs.setCurrentWidget(self.tab_printers))
        self.btn_storage.clicked.connect(lambda: self.tabs.setCurrentWidget(self.tab_storage))
        self.btn_history.clicked.connect(lambda: self.tabs.setCurrentWidget(self.tab_history))
        self.btn_analytics.clicked.connect(lambda: self.tabs.setCurrentWidget(self.tab_analytics))
        self.btn_users.clicked.connect(lambda: self.tabs.setCurrentWidget(self.tab_users))
        self.btn_exit.clicked.connect(self.close)
        if autoupdate:
            self.btn_update.clicked.connect(lambda: autoupdate.check_and_update_gui(self))
        else:
            self.btn_update.clicked.connect(lambda: show_update_error(self))

    def _apply_role_restrictions(self):
        if self.user_role != "admin":
            self.btn_users.setEnabled(False)

    def _fill_tabs(self):
        self.setup_overview_tab()
        self.setup_cabinets_tab()
        self.setup_printers_tab()
        self.setup_storage_tab()
        self.setup_history_tab()
        self.setup_analytics_tab()
        self.setup_users_tab()

    # --- Диалоги и сообщения ---
    def show_error(self, message):
        QMessageBox.critical(self, "Ошибка", message)

    def show_warning(self, message):
        QMessageBox.warning(self, "Предупреждение", message)

    def show_info(self, message):
        QMessageBox.information(self, "Информация", message)

    # --- Остальной код (методы вкладок, обработчики, работа с таблицами) ---
    def setup_overview_tab(self):
        layout = QVBoxLayout(self.tab_overview)
        self.lbl_hello = QLabel(f"<b>Здравствуйте, {self.username}!</b>")
        self.lbl_hello.setStyleSheet("font-size:18px;margin:10px;")
        self.lbl_summary = QLabel("")
        self.lbl_summary.setStyleSheet("font-size:15px;margin:10px;")
        self.lbl_warnings = QLabel("")
        self.lbl_warnings.setStyleSheet("color:red; font-size:14px; margin:10px;")
        layout.addWidget(self.lbl_hello)
        layout.addWidget(self.lbl_summary)
        layout.addWidget(self.lbl_warnings)
        layout.addStretch(1)
        self.refresh_overview()

    def setup_cabinets_tab(self):
        """Настройка вкладки управления кабинетами"""
        layout = QVBoxLayout(self.tab_cabinets)
        title = QLabel("Управление кабинетами")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        self.cabinets_table = QTableWidget(0, 2)
        self.cabinets_table.setHorizontalHeaderLabels(["ID", "Название кабинета"])
        # Позволить пользователю регулировать ширину столбцов вручную
        header = self.cabinets_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        for i in range(self.cabinets_table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.Interactive)
            self.cabinets_table.resizeColumnToContents(i)
        layout.addWidget(self.cabinets_table)
        cabinet_buttons = QHBoxLayout()
        self.btn_add_cabinet = QPushButton("Добавить кабинет")
        self.btn_edit_cabinet = QPushButton("Изменить кабинет")
        self.btn_delete_cabinet = QPushButton("Удалить кабинет")
        cabinet_buttons.addWidget(self.btn_add_cabinet)
        cabinet_buttons.addWidget(self.btn_edit_cabinet)
        cabinet_buttons.addWidget(self.btn_delete_cabinet)
        cabinet_buttons.addStretch()
        layout.addLayout(cabinet_buttons)
        layout.addStretch()
        self.btn_add_cabinet.clicked.connect(self.add_cabinet)
        self.btn_edit_cabinet.clicked.connect(self.edit_cabinet)
        self.btn_delete_cabinet.clicked.connect(self.delete_cabinet)
        if self.user_role == "viewer":
            self.btn_add_cabinet.setEnabled(False)
            self.btn_edit_cabinet.setEnabled(False)
            self.btn_delete_cabinet.setEnabled(False)
        self.refresh_cabinets()
    
    def setup_printers_tab(self):
        """Настройка вкладки управления принтерами"""
        layout = QVBoxLayout(self.tab_printers)
        title = QLabel("Управление принтерами")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        self.printers_table = QTableWidget(0, 8)
        self.printers_table.setHorizontalHeaderLabels([
            "ID", "Кабинет", "Принтер", "Картридж", "Драм",
            "Кол-во картриджей", "Кол-во драмов", "Статус"
        ])
        # Позволить пользователю регулировать ширину столбцов вручную
        header = self.printers_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        # По умолчанию подогнать ширину под содержимое
        for i in range(self.printers_table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.Interactive)
            self.printers_table.resizeColumnToContents(i)
        layout.addWidget(self.printers_table)
        printer_buttons = QHBoxLayout()
        self.btn_add_printer = QPushButton("Добавить принтер")
        self.btn_edit_printer = QPushButton("Изменить принтер")
        self.btn_delete_printer = QPushButton("Удалить принтер")
        self.btn_writeoff_supplies = QPushButton("Списать расходники")
        printer_buttons.addWidget(self.btn_add_printer)
        printer_buttons.addWidget(self.btn_edit_printer)
        printer_buttons.addWidget(self.btn_delete_printer)
        printer_buttons.addWidget(self.btn_writeoff_supplies)
        printer_buttons.addStretch()
        layout.addLayout(printer_buttons)
        layout.addStretch()
        self.btn_add_printer.clicked.connect(self.add_printer)
        self.btn_edit_printer.clicked.connect(self.edit_printer)
        self.btn_delete_printer.clicked.connect(self.delete_printer)
        self.btn_writeoff_supplies.clicked.connect(self.writeoff_supplies)
        if self.user_role == "viewer":
            self.btn_add_printer.setEnabled(False)
            self.btn_edit_printer.setEnabled(False)
            self.btn_delete_printer.setEnabled(False)
            self.btn_writeoff_supplies.setEnabled(False)
        self.refresh_printers()

    def refresh_overview(self):
        try:
            printer_warnings = PrinterManager.get_low_stock_warnings()
            storage_summary = StorageManager.get_storage_summary()
            
            summary_text = (
                f"Картриджей на складе: <b>{storage_summary['cartridges']}</b><br>"
                f"Драмов на складе: <b>{storage_summary['drums']}</b>"
            )
            self.lbl_summary.setText(summary_text)
            
            if printer_warnings:
                self.lbl_warnings.setText("<br>".join(printer_warnings))
            else:
                self.lbl_warnings.setText("")
        except Exception as e:
            self.show_error(f"Не удалось обновить обзор: {e}")

    def setup_storage_tab(self):
        layout = QVBoxLayout(self.tab_storage)
        self.storage_table = QTableWidget(0, 3)
        self.storage_table.setHorizontalHeaderLabels(["Модель", "Тип", "Количество"])
        self.storage_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.storage_table)
        btns = QHBoxLayout()
        self.btn_add_storage = QPushButton("Поступление")
        self.btn_give_storage = QPushButton("Выдать на принтер")
        btns.addWidget(self.btn_add_storage)
        btns.addWidget(self.btn_give_storage)
        layout.addLayout(btns)
        layout.addStretch(1)
        self.btn_add_storage.clicked.connect(self.add_storage)
        self.btn_give_storage.clicked.connect(self.give_storage_to_printer)
        self.storage_table.cellChanged.connect(self.on_storage_cell_changed)
        self.refresh_storage()

    def refresh_storage(self):
        self.storage_table.blockSignals(True)
        storage_items = StorageManager.get_all_storage()
        self.storage_table.setRowCount(len(storage_items))
        for i, item in enumerate(storage_items):
            self.storage_table.setItem(i, 0, QTableWidgetItem(item['model']))
            self.storage_table.setItem(i, 1, QTableWidgetItem(item['type']))
            amount_item = QTableWidgetItem(str(item['amount']))
            amount_item.setFlags(amount_item.flags() | Qt.ItemIsEditable)
            self.storage_table.setItem(i, 2, amount_item)
        self.storage_table.blockSignals(False)

    def on_storage_cell_changed(self, row, column):
        if column != 2:
            return
        model = self.storage_table.item(row, 0).text()
        item_type = self.storage_table.item(row, 1).text()
        value = self.storage_table.item(row, 2).text()
        try:
            amount = int(value)
            if amount < 0:
                raise ValueError
        except ValueError:
            self.show_warning("Введите неотрицательное целое число")
            self.refresh_storage()
            return
        # Обновить количество в базе
        success = StorageManager.set_storage_amount(model, item_type, amount)
        if not success:
            self.show_warning("Не удалось обновить количество на складе")
            self.refresh_storage()

    def setup_history_tab(self):
        # Add similar logical setup for history tab
        pass

    def add_storage(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Поступление на склад")
        form = QFormLayout(dlg)
        model = QLineEdit()
        t = QComboBox(); t.addItems(["cartridge", "drum"])
        amt = QSpinBox(); amt.setMinimum(1); amt.setMaximum(1000)
        form.addRow("Модель:", model)
        form.addRow("Тип:", t)
        form.addRow("Количество:", amt)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form.addWidget(btns)
        btns.accepted.connect(lambda: self.save_new_storage(dlg, model, t, amt))
        btns.rejected.connect(dlg.reject)
        if dlg.exec():
            self.refresh_storage()

    def save_new_storage(self, dlg, model, t, amt):
        m = model.text().strip()
        ty = t.currentText()
        amount = amt.value()
        if not m:
            self.show_warning("Модель не может быть пустой.")
            return
        result = StorageManager.add_to_storage(m, ty, amount, self.username)
        if not result:
            self.show_warning("Не удалось добавить расходники.")
        else:
            dlg.accept()
            
    # --- Методы для работы с кабинетами ---
    def refresh_cabinets(self):
        """Обновление таблицы кабинетов"""
        try:
            cabinets = CabinetManager.get_all_cabinets()
            self.cabinets_table.setRowCount(len(cabinets))
            
            for i, cabinet in enumerate(cabinets):
                self.cabinets_table.setItem(i, 0, QTableWidgetItem(str(cabinet['id'])))
                self.cabinets_table.setItem(i, 1, QTableWidgetItem(cabinet['name']))
        except Exception as e:
            self.show_error(f"Не удалось загрузить кабинеты: {e}")
    
    def add_cabinet(self):
        """Добавление нового кабинета"""
        dialog = CabinetDialog()
        if dialog.exec():
            name = dialog.get_data()
            if not dialog.validate_data():
                return
            if CabinetManager.add_cabinet(name):
                self.refresh_cabinets()
                self.show_info("Кабинет успешно добавлен")
            else:
                self.show_warning("Не удалось добавить кабинет")
    
    def edit_cabinet(self):
        """Редактирование выбранного кабинета"""
        current_row = self.cabinets_table.currentRow()
        if current_row < 0:
            self.show_warning("Выберите кабинет для редактирования")
            return
        cabinet_id = int(self.cabinets_table.item(current_row, 0).text())
        current_name = self.cabinets_table.item(current_row, 1).text()
        dialog = CabinetDialog(current_name, edit_mode=True)
        if dialog.exec():
            new_name = dialog.get_data()
            if not dialog.validate_data():
                return
            if CabinetManager.update_cabinet(cabinet_id, new_name):
                self.refresh_cabinets()
                self.show_info("Кабинет успешно обновлен")
            else:
                self.show_warning("Не удалось обновить кабинет")
    
    def delete_cabinet(self):
        """Удаление выбранного кабинета"""
        current_row = self.cabinets_table.currentRow()
        if current_row < 0:
            self.show_warning("Выберите кабинет для удаления")
            return
        
        cabinet_id = int(self.cabinets_table.item(current_row, 0).text())
        cabinet_name = self.cabinets_table.item(current_row, 1).text()
        
        reply = QMessageBox.question(
            self, "Подтверждение", 
            f"Вы действительно хотите удалить кабинет '{cabinet_name}'?\n\n"
            f"Внимание: все принтеры в этом кабинете также будут удалены!",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if CabinetManager.delete_cabinet(cabinet_id):
                self.refresh_cabinets()
                self.refresh_printers()  # Обновляем принтеры так как они могли быть удалены
                self.show_info("Кабинет успешно удален")
            else:
                self.show_warning("Не удалось удалить кабинет")
    
    # --- Методы для работы с принтерами ---
    def refresh_printers(self):
        """Обновление таблицы принтеров"""
        try:
            printers = PrinterManager.get_all_printers()
            self.printers_table.setRowCount(len(printers))
            
            for i, printer in enumerate(printers):
                self.printers_table.setItem(i, 0, QTableWidgetItem(str(printer['id'])))
                self.printers_table.setItem(i, 1, QTableWidgetItem(printer['cabinet_name'] or "Без кабинета"))
                self.printers_table.setItem(i, 2, QTableWidgetItem(printer['name']))
                self.printers_table.setItem(i, 3, QTableWidgetItem(printer['cartridge'] or ""))
                self.printers_table.setItem(i, 4, QTableWidgetItem(printer['drum'] or ""))
                self.printers_table.setItem(i, 5, QTableWidgetItem(str(printer['cartridge_amount'] or 0)))
                self.printers_table.setItem(i, 6, QTableWidgetItem(str(printer['drum_amount'] or 0)))
                
                # Определение статуса
                status = "Норма"
                min_cart = printer['min_cartridge_amount'] or 0
                min_drum = printer['min_drum_amount'] or 0
                cart_amt = printer['cartridge_amount'] or 0
                drum_amt = printer['drum_amount'] or 0
                
                if cart_amt < 0 or drum_amt < 0:
                    status = "Ошибка"
                elif (min_cart > 0 and cart_amt < min_cart) or (min_drum > 0 and drum_amt < min_drum):
                    status = "Нужно пополнение"
                
                status_item = QTableWidgetItem(status)
                if status == "Ошибка":
                    status_item.setBackground(QColor(255, 200, 200))  # Красный
                elif status == "Нужно пополнение":
                    status_item.setBackground(QColor(255, 255, 200))  # Желтый
                
                self.printers_table.setItem(i, 7, status_item)
                
        except Exception as e:
            self.show_error(f"Не удалось загрузить принтеры: {e}")
    
    def add_printer(self):
        """Добавление нового принтера"""
        dialog = PrinterDialog()
        if dialog.exec():
            data = dialog.get_data()
            if not dialog.validate_data():
                return
            # Только нужные поля для создания
            add_data = {
                'cabinet_id': data['cabinet_id'],
                'name': data['name'],
                'cartridge': data['cartridge'],
                'drum': data['drum'],
            }
            if PrinterManager.add_printer(**add_data):
                # Получаем id только что добавленного принтера
                printers = PrinterManager.get_all_printers()
                new_printer = next((p for p in printers if p['name'] == data['name'] and p['cabinet_name'] == self.get_cabinet_name_by_id(data['cabinet_id'])), None)
                if new_printer:
                    PrinterManager.update_printer(
                        new_printer['id'],
                        min_cartridge_amount=data['min_cartridge_amount'],
                        min_drum_amount=data['min_drum_amount']
                    )
                self.refresh_printers()
                self.show_info("Принтер успешно добавлен")
            else:
                self.show_warning("Не удалось добавить принтер")

    def get_cabinet_name_by_id(self, cabinet_id):
        cabinets = CabinetManager.get_all_cabinets()
        for cab in cabinets:
            if cab['id'] == cabinet_id:
                return cab['name']
        return ""

    def edit_printer(self):
        """Редактирование выбранного принтера"""
        current_row = self.printers_table.currentRow()
        if current_row < 0:
            self.show_warning("Выберите принтер для редактирования")
            return
        printer_id = int(self.printers_table.item(current_row, 0).text())
        printers = PrinterManager.get_all_printers()
        current_printer = next((p for p in printers if p['id'] == printer_id), None)
        if not current_printer:
            self.show_warning("Принтер не найден")
            return
        dialog = PrinterDialog(current_printer)
        if dialog.exec():
            data = dialog.get_data()
            if not dialog.validate_data():
                return
            if PrinterManager.update_printer(printer_id, **data):
                self.refresh_printers()
                self.show_info("Принтер успешно обновлен")
            else:
                self.show_warning("Не удалось обновить принтер")
    
    def delete_printer(self):
        """Удаление выбранного принтера"""
        current_row = self.printers_table.currentRow()
        if current_row < 0:
            self.show_warning("Выберите принтер для удаления")
            return
        
        printer_id = int(self.printers_table.item(current_row, 0).text())
        printer_name = self.printers_table.item(current_row, 2).text()
        
        reply = QMessageBox.question(
            self, "Подтверждение", 
            f"Вы действительно хотите удалить принтер '{printer_name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if PrinterManager.delete_printer(printer_id):
                self.refresh_printers()
                self.show_info("Принтер успешно удален")
            else:
                self.show_warning("Не удалось удалить принтер")
    
    def writeoff_supplies(self):
        """Списание (замена) расходников с принтера с учётом в аналитике."""
        current_row = self.printers_table.currentRow()
        if current_row < 0:
            self.show_warning("Выберите принтер для списания расходников")
            return
        printer_id = int(self.printers_table.item(current_row, 0).text())
        printer_name = self.printers_table.item(current_row, 2).text()
        dialog = WriteoffDialog(printer_name)
        if dialog.exec():
            cart_writeoff = dialog.cartridge_spin.value()
            drum_writeoff = dialog.drum_spin.value()
            if cart_writeoff == 0 and drum_writeoff == 0:
                self.show_warning("Введите количество для списания")
                return
            # Новый способ: сразу учитываем замену в базе и аналитике
            success = StorageManager.add_writeoff_record(
                printer_id=printer_id,
                writeoff_cartridge=cart_writeoff,
                writeoff_drum=drum_writeoff,
                username=self.username
            )
            if success:
                self.refresh_printers()
                QMessageBox.information(self, "Успех", "Замена успешно учтена и добавлена в аналитику")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось провести замену расходников")

    def give_storage_to_printer(self):
        current_row = self.storage_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "Предупреждение", "Выберите позицию на складе для выдачи")
            return
        model = self.storage_table.item(current_row, 0).text()
        item_type = self.storage_table.item(current_row, 1).text()
        max_amount = int(self.storage_table.item(current_row, 2).text())
        if max_amount <= 0:
            QMessageBox.warning(self, "Ошибка", "Нет доступного количества для выдачи")
            return
        # Получить список совместимых принтеров
        printers = StorageManager.get_compatible_printers(model, item_type)
        if not printers:
            QMessageBox.warning(self, "Ошибка", "Нет принтеров, совместимых с этим расходником")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Выдать на принтер")
        form = QFormLayout(dlg)
        printer_combo = QComboBox()
        printer_ids = []
        for p in printers:
            printer_combo.addItem(p['name'])
            printer_ids.append(p['id'])
        amt = QSpinBox(); amt.setMinimum(1); amt.setMaximum(max_amount)
        form.addRow("Принтер:", printer_combo)
        form.addRow("Количество:", amt)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec():
            printer_id = printer_ids[printer_combo.currentIndex()]
            amount = amt.value()
            success = StorageManager.transfer_to_printer(model, item_type, amount, printer_id, self.username)
            if success:
                self.refresh_storage()
                self.refresh_printers()
                QMessageBox.information(self, "Успех", "Расходники успешно выданы на принтер")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось выдать расходники на принтер")

    def setup_analytics_tab(self):
        layout = QVBoxLayout(self.tab_analytics)
        # --- Таблица расхода по месяцам ---
        self.analytics_usage_table = QTableWidget()
        self.analytics_usage_table.setColumnCount(2)
        self.analytics_usage_table.setHorizontalHeaderLabels(["Месяц", "Расход картриджей"])
        layout.addWidget(QLabel("Расход картриджей по месяцам:"))
        layout.addWidget(self.analytics_usage_table)
        # --- Топ-5 моделей ---
        self.analytics_top5_table = QTableWidget()
        self.analytics_top5_table.setColumnCount(2)
        self.analytics_top5_table.setHorizontalHeaderLabels(["Модель", "Всего расход"])
        layout.addWidget(QLabel("Топ-5 моделей картриджей по расходу:"))
        layout.addWidget(self.analytics_top5_table)
        # --- Отчёт по заменам ---
        self.analytics_report_table = QTableWidget()
        self.analytics_report_table.setColumnCount(6)
        self.analytics_report_table.setHorizontalHeaderLabels([
            "Кабинет", "Принтер", "Картридж", "Замен", "Последняя замена", "Дней прошло"
        ])
        layout.addWidget(QLabel("Отчёт по заменам картриджей:"))
        layout.addWidget(self.analytics_report_table)
        # --- Прогноз по модели ---
        self.forecast_combo = QComboBox()
        self.forecast_combo.setEditable(False)
        self.forecast_label = QLabel("")
        layout.addWidget(QLabel("Прогноз расхода по модели:"))
        layout.addWidget(self.forecast_combo)
        layout.addWidget(self.forecast_label)
        # --- Кнопки ---
        btns = QHBoxLayout()
        self.btn_plot_usage = QPushButton("Показать график")
        self.btn_export_usage = QPushButton("Экспорт в Excel")
        self.btn_refresh_analytics = QPushButton("Обновить")
        btns.addWidget(self.btn_plot_usage)
        btns.addWidget(self.btn_export_usage)
        btns.addWidget(self.btn_refresh_analytics)
        layout.addLayout(btns)
        layout.addStretch(1)
        self.btn_plot_usage.clicked.connect(self.on_plot_usage)
        self.btn_export_usage.clicked.connect(self.on_export_usage)
        self.btn_refresh_analytics.clicked.connect(self.refresh_analytics_tab)
        self.forecast_combo.currentTextChanged.connect(self.on_forecast_model_changed)
        self.refresh_analytics_tab()

    def refresh_analytics_tab(self):
        # --- Заполняем таблицу расхода по месяцам ---
        usage_df = get_cartridge_usage_by_month()
        self.analytics_usage_table.setRowCount(len(usage_df))
        for i, row in usage_df.iterrows():
            self.analytics_usage_table.setItem(i, 0, QTableWidgetItem(str(row["month"])))
            self.analytics_usage_table.setItem(i, 1, QTableWidgetItem(str(row["usage"])))
        # --- Топ-5 моделей ---
        top5_df = get_top5_cartridge_models()
        self.analytics_top5_table.setRowCount(len(top5_df))
        for i, row in top5_df.iterrows():
            self.analytics_top5_table.setItem(i, 0, QTableWidgetItem(str(row["model"])))
            self.analytics_top5_table.setItem(i, 1, QTableWidgetItem(str(row["total"])))
        # --- Отчёт по заменам ---
        report = get_cartridge_change_report()
        self.analytics_report_table.setRowCount(len(report))
        for i, row in enumerate(report):
            self.analytics_report_table.setItem(i, 0, QTableWidgetItem(str(row["cabinet"])))
            self.analytics_report_table.setItem(i, 1, QTableWidgetItem(str(row["printer"])))
            self.analytics_report_table.setItem(i, 2, QTableWidgetItem(str(row["cartridge"])))
            self.analytics_report_table.setItem(i, 3, QTableWidgetItem(str(row["total_changes"])))
            self.analytics_report_table.setItem(i, 4, QTableWidgetItem(str(row["last_change"])))
            self.analytics_report_table.setItem(i, 5, QTableWidgetItem(str(row["days_since_last"])))
        # --- Прогноз по модели ---
        self.forecast_combo.blockSignals(True)
        self.forecast_combo.clear()
        models = list(top5_df["model"]) if not top5_df.empty else []
        self.forecast_combo.addItems(models)
        self.forecast_combo.blockSignals(False)
        self.on_forecast_model_changed()

    def on_forecast_model_changed(self):
        model = self.forecast_combo.currentText()
        if not model:
            self.forecast_label.setText("")
            return
        forecast = get_cartridge_forecast(model)
        if forecast:
            self.forecast_label.setText(
                f"Средний расход: <b>{forecast['avg_per_month']:.1f}</b> шт/мес<br>"
                f"Рекомендуемый запас: <b>{forecast['recommended_stock']}</b> шт"
            )
        else:
            self.forecast_label.setText("Нет данных по расходу")

    def on_plot_usage(self):
        usage_df = get_cartridge_usage_by_month()
        plot_cartridge_usage(usage_df)

    def on_export_usage(self):
        usage_df = get_cartridge_usage_by_month()
        export_cartridge_usage_to_excel(usage_df)
        QMessageBox.information(self, "Экспорт", "Файл cartridge_usage.xlsx сохранён.")

    def setup_users_tab(self):
        layout = QVBoxLayout(self.tab_users)
        self.users_table = QTableWidget(0, 3)
        self.users_table.setHorizontalHeaderLabels(["ID", "Логин", "Роль"])
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.users_table)
        btns = QHBoxLayout()
        self.btn_add_user = QPushButton("Добавить пользователя")
        self.btn_edit_user = QPushButton("Изменить пользователя")
        self.btn_delete_user = QPushButton("Удалить пользователя")
        self.btn_reset_password = QPushButton("Сбросить пароль")
        self.btn_change_own_password = QPushButton("Сменить мой пароль")
        btns.addWidget(self.btn_add_user)
        btns.addWidget(self.btn_edit_user)
        btns.addWidget(self.btn_delete_user)
        btns.addWidget(self.btn_reset_password)
        btns.addWidget(self.btn_change_own_password)
        layout.addLayout(btns)
        layout.addStretch(1)
        self.btn_add_user.clicked.connect(self.add_user)
        self.btn_edit_user.clicked.connect(self.edit_user)
        self.btn_delete_user.clicked.connect(self.delete_user)
        self.btn_reset_password.clicked.connect(self.reset_password)
        self.btn_change_own_password.clicked.connect(self.change_own_password)
        self.refresh_users()
        if self.user_role != "admin":
            self.btn_add_user.setEnabled(False)
            self.btn_edit_user.setEnabled(False)
            self.btn_delete_user.setEnabled(False)
            self.btn_reset_password.setEnabled(False)

    def refresh_users(self):
        users = UserManager.get_all_users()
        self.users_table.setRowCount(len(users))
        for i, user in enumerate(users):
            self.users_table.setItem(i, 0, QTableWidgetItem(str(user['id'])))
            self.users_table.setItem(i, 1, QTableWidgetItem(user['login']))
            self.users_table.setItem(i, 2, QTableWidgetItem(user['role']))

    def add_user(self):
        dialog = UserDialog()
        if dialog.exec():
            login, password, role = dialog.get_data()
            if not dialog.validate_data():
                return
            if UserManager.add_user(login, password, role):
                self.refresh_users()
                self.show_info("Пользователь успешно добавлен")
            else:
                self.show_warning("Не удалось добавить пользователя (возможно, логин уже занят)")

    def edit_user(self):
        current_row = self.users_table.currentRow()
        if current_row < 0:
            self.show_warning("Выберите пользователя для редактирования")
            return
        user_id = int(self.users_table.item(current_row, 0).text())
        login = self.users_table.item(current_row, 1).text()
        role = self.users_table.item(current_row, 2).text()
        dialog = UserDialog(login, role, edit_mode=True)
        if dialog.exec():
            new_login, new_password, new_role = dialog.get_data()
            if not dialog.validate_data():
                return
            if UserManager.update_user(user_id, new_login, new_password, new_role):
                self.refresh_users()
                self.show_info("Пользователь успешно обновлён")
            else:
                self.show_warning("Не удалось обновить пользователя")

    def delete_user(self):
        current_row = self.users_table.currentRow()
        if current_row < 0:
            self.show_warning("Выберите пользователя для удаления")
            return
        user_id = int(self.users_table.item(current_row, 0).text())
        login = self.users_table.item(current_row, 1).text()
        if login == self.username:
            self.show_warning("Нельзя удалить самого себя!")
            return
        reply = QMessageBox.question(self, "Подтверждение", f"Удалить пользователя '{login}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if UserManager.delete_user(user_id):
                self.refresh_users()
                self.show_info("Пользователь удалён")
            else:
                self.show_warning("Не удалось удалить пользователя")

    def reset_password(self):
        current_row = self.users_table.currentRow()
        if current_row < 0:
            self.show_warning("Выберите пользователя для сброса пароля")
            return
        user_id = int(self.users_table.item(current_row, 0).text())
        login = self.users_table.item(current_row, 1).text()
        import random, string
        new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        if UserManager.update_user(user_id, login, new_password, self.users_table.item(current_row, 2).text()):
            dlg = ResetPasswordDialog(new_password, self)
            dlg.exec()
            self.show_info("Пароль успешно сброшен")
        else:
            self.show_warning("Не удалось сбросить пароль")

    def change_own_password(self):
        user_id = None
        users = UserManager.get_all_users()
        for user in users:
            if user['login'] == self.username:
                user_id = user['id']
                break
        if user_id is None:
            self.show_warning("Пользователь не найден")
            return
        dialog = UserDialog(self.username, role=self.user_role, edit_mode=True)
        if dialog.exec():
            _, new_password, _ = dialog.get_data()
            if not new_password:
                self.show_warning("Введите новый пароль")
                return
            if UserManager.update_user(user_id, self.username, new_password, self.user_role):
                self.show_info("Пароль успешно изменён")
            else:
                self.show_warning("Не удалось изменить пароль")
