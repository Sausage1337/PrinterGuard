import sys
import sqlite3
import hashlib
import analytics
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QPushButton, QListWidget, QLabel, QDialog, QFormLayout, QLineEdit, QSpinBox,
    QDialogButtonBox, QComboBox, QTextEdit, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog
)
from PySide6.QtGui import QColor
import autoupdate


DB_FILE = "office.db"

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        login TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    )''')
    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (login, password, role) VALUES (?, ?, ?)",
                  ("admin", hash_password("admin"), "admin"))
    c.execute('''CREATE TABLE IF NOT EXISTS cabinets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS printers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cabinet_id INTEGER,
        name TEXT NOT NULL,
        cartridge TEXT,
        drum TEXT,
        cartridge_amount INTEGER DEFAULT 0,
        drum_amount INTEGER DEFAULT 0,
        min_cartridge_amount INTEGER DEFAULT 0,
        min_drum_amount INTEGER DEFAULT 0,
        FOREIGN KEY (cabinet_id) REFERENCES cabinets(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS writeoff_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        printer_id INTEGER,
        writeoff_cartridge INTEGER DEFAULT 0,
        writeoff_drum INTEGER DEFAULT 0,
        datetime TEXT NOT NULL,
        username TEXT,
        FOREIGN KEY (printer_id) REFERENCES printers(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS storage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model TEXT NOT NULL,
        type TEXT CHECK(type IN ('cartridge','drum')) NOT NULL,
        amount INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS storage_transfer_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        datetime TEXT NOT NULL,
        username TEXT,
        model TEXT NOT NULL,
        type TEXT CHECK(type IN ('cartridge','drum')) NOT NULL,
        amount INTEGER NOT NULL,
        from_place TEXT,
        to_place TEXT
    )''')
    conn.commit()
    conn.close()

class LoginDialog(QDialog):
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
        return self.login_edit.text(), self.pass_edit.text()

class UserDialog(QDialog):
    def __init__(self, login="", role="operator", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Пользователь")
        layout = QFormLayout(self)
        self.login_edit = QLineEdit(login)
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.Password)
        self.role_box = QComboBox()
        self.role_box.addItems(["admin", "operator", "viewer"])
        self.role_box.setCurrentText(role)
        layout.addRow("Логин:", self.login_edit)
        layout.addRow("Пароль:", self.pass_edit)
        layout.addRow("Роль:", self.role_box)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        return self.login_edit.text(), self.pass_edit.text(), self.role_box.currentText()

class MainWindow(QMainWindow):
    def __init__(self, user_role, username, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Учёт принтеров и расходников")
        self.resize(1280, 750)
        self.user_role = user_role
        self.username = username

        # --- Боковое меню ---
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

        # --- Центральные вкладки ---
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

        # --- Основной компоновщик ---
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        main_layout.addWidget(self.menu_widget, 0)
        main_layout.addWidget(self.tabs, 1)
        self.setCentralWidget(central_widget)

        # --- Обработка навигации по меню ---
        self.btn_overview.clicked.connect(lambda: self.tabs.setCurrentWidget(self.tab_overview))
        self.btn_cabinets.clicked.connect(lambda: self.tabs.setCurrentWidget(self.tab_cabinets))
        self.btn_printers.clicked.connect(lambda: self.tabs.setCurrentWidget(self.tab_printers))
        self.btn_storage.clicked.connect(lambda: self.tabs.setCurrentWidget(self.tab_storage))
        self.btn_history.clicked.connect(lambda: self.tabs.setCurrentWidget(self.tab_history))
        self.btn_analytics.clicked.connect(lambda: self.tabs.setCurrentWidget(self.tab_analytics))
        self.btn_users.clicked.connect(lambda: self.tabs.setCurrentWidget(self.tab_users))
        self.btn_update.clicked.connect(lambda: autoupdate.check_and_update_gui(self))
        self.btn_exit.clicked.connect(self.close)

        # --- Ограничения по ролям ---
        if self.user_role != "admin":
            self.btn_users.setEnabled(False)

        # --- Заполнение вкладок ---
        self.setup_overview_tab()
        self.setup_cabinets_tab()
        self.setup_printers_tab()
        self.setup_storage_tab()
        self.setup_history_tab()
        self.setup_analytics_tab()
        self.setup_users_tab()

        self.tabs.setCurrentWidget(self.tab_overview)

    # ========== OVERVIEW ==========
    def setup_overview_tab(self):
        layout = QVBoxLayout(self.tab_overview)
        self.lbl_hello = QLabel(f"<b>Здравствуйте, {self.username}!</b>")
        self.lbl_hello.setStyleSheet("font-size:18px;margin:10px;")
        self.lbl_summary = QLabel("")
        self.lbl_summary.setStyleSheet("font-size:15px;margin:10px;")
        layout.addWidget(self.lbl_hello)
        layout.addWidget(self.lbl_summary)
        layout.addStretch(1)
        self.refresh_overview()

    def refresh_overview(self):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM cabinets")
        cab_count = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM printers")
        prn_count = c.fetchone()[0]
        c.execute("SELECT SUM(amount) FROM storage WHERE type='cartridge'")
        cart_sum = c.fetchone()[0] or 0
        c.execute("SELECT SUM(amount) FROM storage WHERE type='drum'")
        drum_sum = c.fetchone()[0] or 0
        conn.close()
        text = (
            f"Кабинетов: <b>{cab_count}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Принтеров: <b>{prn_count}</b><br>"
            f"Картриджей на складе: <b>{cart_sum}</b> &nbsp;&nbsp;|&nbsp;&nbsp; "
            f"Драмов на складе: <b>{drum_sum}</b>"
        )
        self.lbl_summary.setText(text)

    # ========== CABINETS ==========
    def setup_cabinets_tab(self):
        layout = QVBoxLayout(self.tab_cabinets)
        h = QHBoxLayout()
        self.cabinet_list = QListWidget()
        self.cabinet_list.setMaximumWidth(300)
        self.cabinet_list.itemClicked.connect(self.show_cabinet_printers)
        h.addWidget(self.cabinet_list)
        self.cabinet_printer_table = QTableWidget(0, 5)
        self.cabinet_printer_table.setHorizontalHeaderLabels(["Принтер", "Картридж", "Драм", "Картр.", "Драм"])
        self.cabinet_printer_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        h.addWidget(self.cabinet_printer_table, 2)
        layout.addLayout(h)

        btns = QHBoxLayout()
        self.btn_add_cabinet = QPushButton("Добавить кабинет")
        self.btn_del_cabinet = QPushButton("Удалить кабинет")
        btns.addWidget(self.btn_add_cabinet)
        btns.addWidget(self.btn_del_cabinet)
        layout.addLayout(btns)
        layout.addStretch(1)

        self.btn_add_cabinet.clicked.connect(self.add_cabinet)
        self.btn_del_cabinet.clicked.connect(self.delete_cabinet)
        self.refresh_cabinets()

    def refresh_cabinets(self):
        self.cabinet_list.clear()
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, name FROM cabinets ORDER BY name")
        self.cabinets = c.fetchall()
        for cabid, name in self.cabinets:
            self.cabinet_list.addItem(f"{name} (ID: {cabid})")
        conn.close()
        self.cabinet_printer_table.setRowCount(0)

    def add_cabinet(self):
        name, ok = QInputDialog.getText(self, "Добавить кабинет", "Название кабинета:")
        if ok and name.strip():
            try:
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("INSERT INTO cabinets (name) VALUES (?)", (name.strip(),))
                conn.commit()
                conn.close()
                self.refresh_cabinets()
                self.refresh_overview()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Ошибка", "Кабинет с таким названием уже существует!")

    def delete_cabinet(self):
        idx = self.cabinet_list.currentRow()
        if idx < 0 or idx >= len(self.cabinets):
            return
        cabid, name = self.cabinets[idx]
        reply = QMessageBox.question(self, "Удалить кабинет",
                                     f"Удалить кабинет '{name}' и все его принтеры?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("DELETE FROM printers WHERE cabinet_id=?", (cabid,))
            c.execute("DELETE FROM cabinets WHERE id=?", (cabid,))
            conn.commit()
            conn.close()
            self.refresh_cabinets()
            self.refresh_overview()

    def show_cabinet_printers(self, item):
        cabid = int(item.text().split("ID:")[1].strip(") "))
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT name, cartridge, drum, cartridge_amount, drum_amount FROM printers WHERE cabinet_id=?", (cabid,))
        printers = c.fetchall()
        self.cabinet_printer_table.setRowCount(len(printers))
        for i, (name, cart, drum, cart_amt, drum_amt) in enumerate(printers):
            self.cabinet_printer_table.setItem(i, 0, QTableWidgetItem(name))
            self.cabinet_printer_table.setItem(i, 1, QTableWidgetItem(cart or "-"))
            self.cabinet_printer_table.setItem(i, 2, QTableWidgetItem(drum or "-"))
            self.cabinet_printer_table.setItem(i, 3, QTableWidgetItem(str(cart_amt)))
            self.cabinet_printer_table.setItem(i, 4, QTableWidgetItem(str(drum_amt)))
        conn.close()

    # ========== PRINTERS ==========
    def setup_printers_tab(self):
        layout = QVBoxLayout(self.tab_printers)
        self.printer_table = QTableWidget(0, 8)
        self.printer_table.setHorizontalHeaderLabels([
            "Кабинет", "Принтер", "Картридж", "Драм", "Картр.", "Драм", "Мин. Картр.", "Мин. Драм"
        ])
        self.printer_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.printer_table)

        btns = QHBoxLayout()
        self.btn_add_printer = QPushButton("Добавить принтер")
        self.btn_edit_printer = QPushButton("Редактировать")
        self.btn_del_printer = QPushButton("Удалить")
        self.btn_writeoff = QPushButton("Списать расходник")
        btns.addWidget(self.btn_add_printer)
        btns.addWidget(self.btn_edit_printer)
        btns.addWidget(self.btn_del_printer)
        btns.addWidget(self.btn_writeoff)
        layout.addLayout(btns)
        layout.addStretch(1)

        self.btn_add_printer.clicked.connect(self.add_printer)
        self.btn_edit_printer.clicked.connect(self.edit_printer)
        self.btn_del_printer.clicked.connect(self.delete_printer)
        self.btn_writeoff.clicked.connect(self.writeoff_printer)
        self.refresh_printers()

    def refresh_printers(self):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''SELECT cabinets.name, printers.id, printers.name, printers.cartridge, printers.drum,
                    printers.cartridge_amount, printers.drum_amount, printers.min_cartridge_amount, printers.min_drum_amount
                     FROM printers
                     LEFT JOIN cabinets ON printers.cabinet_id = cabinets.id
                     ORDER BY cabinets.name, printers.name''')
        rows = c.fetchall()
        self.printer_table.setRowCount(len(rows))
        self.printers = []
        for i, (cab, pid, prn, cart, drum, cart_amt, drum_amt, min_cart, min_drum) in enumerate(rows):
            self.printers.append((pid, cab, prn, cart, drum, cart_amt, drum_amt, min_cart, min_drum))
            self.printer_table.setItem(i, 0, QTableWidgetItem(cab or "-"))
            self.printer_table.setItem(i, 1, QTableWidgetItem(prn))
            self.printer_table.setItem(i, 2, QTableWidgetItem(cart or "-"))
            self.printer_table.setItem(i, 3, QTableWidgetItem(drum or "-"))
            self.printer_table.setItem(i, 4, QTableWidgetItem(str(cart_amt)))
            self.printer_table.setItem(i, 5, QTableWidgetItem(str(drum_amt)))
            self.printer_table.setItem(i, 6, QTableWidgetItem(str(min_cart)))
            self.printer_table.setItem(i, 7, QTableWidgetItem(str(min_drum)))
        conn.close()

    def add_printer(self):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, name FROM cabinets ORDER BY name")
        cabs = c.fetchall()
        conn.close()
        if not cabs:
            QMessageBox.warning(self, "Ошибка", "Нет ни одного кабинета.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Новый принтер")
        form = QFormLayout(dlg)
        cb_cab = QComboBox()
        for cid, name in cabs:
            cb_cab.addItem(name, cid)
        name_edit = QLineEdit()
        cart_edit = QLineEdit()
        drum_edit = QLineEdit()
        cart_amt = QSpinBox(); cart_amt.setMaximum(1000)
        drum_amt = QSpinBox(); drum_amt.setMaximum(1000)
        min_cart = QSpinBox(); min_cart.setMaximum(100)
        min_drum = QSpinBox(); min_drum.setMaximum(100)
        form.addRow("Кабинет:", cb_cab)
        form.addRow("Название:", name_edit)
        form.addRow("Модель картриджа:", cart_edit)
        form.addRow("Модель драма:", drum_edit)
        form.addRow("Кол-во картриджей:", cart_amt)
        form.addRow("Кол-во драмов:", drum_amt)
        form.addRow("Мин. картриджей:", min_cart)
        form.addRow("Мин. драмов:", min_drum)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec():
            cabid = cb_cab.currentData()
            name = name_edit.text().strip()
            cart = cart_edit.text().strip()
            drum = drum_edit.text().strip()
            ca = cart_amt.value()
            da = drum_amt.value()
            mca = min_cart.value()
            mda = min_drum.value()
            if not name:
                QMessageBox.warning(self, "Ошибка", "Название принтера не может быть пустым.")
                return
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''INSERT INTO printers (cabinet_id, name, cartridge, drum, cartridge_amount, drum_amount, min_cartridge_amount, min_drum_amount)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                         (cabid, name, cart, drum, ca, da, mca, mda))
            conn.commit()
            conn.close()
            self.refresh_printers()
            self.refresh_overview()

    def edit_printer(self):
        idx = self.printer_table.currentRow()
        if idx < 0 or idx >= len(self.printers):
            return
        pid, cab, name, cart, drum, cart_amt, drum_amt, min_cart, min_drum = self.printers[idx]
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, name FROM cabinets ORDER BY name")
        cabs = c.fetchall()
        conn.close()
        dlg = QDialog(self)
        dlg.setWindowTitle("Редактировать принтер")
        form = QFormLayout(dlg)
        cb_cab = QComboBox()
        for cid, cname in cabs:
            cb_cab.addItem(cname, cid)
            if cname == cab:
                cb_cab.setCurrentText(cab)
        name_edit = QLineEdit(name)
        cart_edit = QLineEdit(cart)
        drum_edit = QLineEdit(drum)
        cart_amt_spin = QSpinBox(); cart_amt_spin.setValue(cart_amt); cart_amt_spin.setMaximum(1000)
        drum_amt_spin = QSpinBox(); drum_amt_spin.setValue(drum_amt); drum_amt_spin.setMaximum(1000)
        min_cart_spin = QSpinBox(); min_cart_spin.setValue(min_cart); min_cart_spin.setMaximum(100)
        min_drum_spin = QSpinBox(); min_drum_spin.setValue(min_drum); min_drum_spin.setMaximum(100)
        form.addRow("Кабинет:", cb_cab)
        form.addRow("Название:", name_edit)
        form.addRow("Модель картриджа:", cart_edit)
        form.addRow("Модель драма:", drum_edit)
        form.addRow("Кол-во картриджей:", cart_amt_spin)
        form.addRow("Кол-во драмов:", drum_amt_spin)
        form.addRow("Мин. картриджей:", min_cart_spin)
        form.addRow("Мин. драмов:", min_drum_spin)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec():
            cabid = cb_cab.currentData()
            new_name = name_edit.text().strip()
            new_cart = cart_edit.text().strip()
            new_drum = drum_edit.text().strip()
            ca = cart_amt_spin.value()
            da = drum_amt_spin.value()
            mca = min_cart_spin.value()
            mda = min_drum_spin.value()
            if not new_name:
                QMessageBox.warning(self, "Ошибка", "Название принтера не может быть пустым.")
                return
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute('''UPDATE printers SET cabinet_id=?, name=?, cartridge=?, drum=?, cartridge_amount=?, drum_amount=?, min_cartridge_amount=?, min_drum_amount=?
                         WHERE id=?''',
                         (cabid, new_name, new_cart, new_drum, ca, da, mca, mda, pid))
            conn.commit()
            conn.close()
            self.refresh_printers()
            self.refresh_overview()

    def delete_printer(self):
        idx = self.printer_table.currentRow()
        if idx < 0 or idx >= len(self.printers):
            return
        pid, cab, name, *_ = self.printers[idx]
        reply = QMessageBox.question(self, "Удалить принтер", f"Удалить принтер '{name}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("DELETE FROM printers WHERE id=?", (pid,))
            conn.commit()
            conn.close()
            self.refresh_printers()
            self.refresh_overview()

    def writeoff_printer(self):
        idx = self.printer_table.currentRow()
        if idx < 0 or idx >= len(self.printers):
            return
        pid, cab, name, cart, drum, cart_amt, drum_amt, *_ = self.printers[idx]
        dlg = QDialog(self)
        dlg.setWindowTitle("Списать расходник")
        form = QFormLayout(dlg)
        spin_cart = QSpinBox(); spin_cart.setMaximum(cart_amt); spin_cart.setValue(0)
        spin_drum = QSpinBox(); spin_drum.setMaximum(drum_amt); spin_drum.setValue(0)
        form.addRow(f"Списать картриджей (макс {cart_amt}):", spin_cart)
        form.addRow(f"Списать драмов (макс {drum_amt}):", spin_drum)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec():
            wc = spin_cart.value()
            wd = spin_drum.value()
            if wc == 0 and wd == 0:
                return
            if wc > cart_amt or wd > drum_amt:
                QMessageBox.warning(self, "Ошибка", "Нельзя списать больше, чем есть.")
                return
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE printers SET cartridge_amount=cartridge_amount-?, drum_amount=drum_amount-? WHERE id=?",
                      (wc, wd, pid))
            c.execute("INSERT INTO writeoff_history (printer_id, writeoff_cartridge, writeoff_drum, datetime, username) VALUES (?, ?, ?, ?, ?)",
                      (pid, wc, wd, now, self.username))
            conn.commit()
            conn.close()
            self.refresh_printers()
            self.refresh_overview()

    # ========== STORAGE ==========
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
        self.btn_give_storage.clicked.connect(self.give_storage)
        self.refresh_storage()

    def refresh_storage(self):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT model, type, amount FROM storage ORDER BY type, model")
        rows = c.fetchall()
        self.storage_table.setRowCount(len(rows))
        self.storage = []
        for i, (model, t, amt) in enumerate(rows):
            self.storage.append((model, t, amt))
            self.storage_table.setItem(i, 0, QTableWidgetItem(model))
            self.storage_table.setItem(i, 1, QTableWidgetItem(t))
            self.storage_table.setItem(i, 2, QTableWidgetItem(str(amt)))
        conn.close()
        self.refresh_overview()

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
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec():
            m = model.text().strip()
            ty = t.currentText()
            amount = amt.value()
            if not m:
                QMessageBox.warning(self, "Ошибка", "Модель не может быть пустой.")
                return
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT id FROM storage WHERE model=? AND type=?", (m, ty))
            row = c.fetchone()
            if row:
                c.execute("UPDATE storage SET amount=amount+? WHERE id=?", (amount, row[0]))
            else:
                c.execute("INSERT INTO storage (model, type, amount) VALUES (?, ?, ?)", (m, ty, amount))
            c.execute("INSERT INTO storage_transfer_history (datetime, username, model, type, amount, from_place, to_place) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.username, m, ty, amount, "внешние поставки", "склад"))
            conn.commit()
            conn.close()
            self.refresh_storage()

    def give_storage(self):
        idx = self.storage_table.currentRow()
        if idx < 0 or idx >= len(self.storage):
            return
        model, t, amt = self.storage[idx]
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        if t == "cartridge":
            c.execute("SELECT id, name FROM printers WHERE cartridge=?", (model,))
        else:
            c.execute("SELECT id, name FROM printers WHERE drum=?", (model,))
        prns = c.fetchall()
        conn.close()
        if not prns:
            QMessageBox.warning(self, "Ошибка", "Нет принтеров для выдачи данного расходника.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Выдать на принтер")
        form = QFormLayout(dlg)
        cb = QComboBox()
        for pid, pname in prns:
            cb.addItem(pname, pid)
        give_amt = QSpinBox(); give_amt.setMinimum(1); give_amt.setMaximum(amt)
        form.addRow("Принтер:", cb)
        form.addRow("Количество:", give_amt)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec():
            pid = cb.currentData()
            a = give_amt.value()
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE storage SET amount=amount-? WHERE model=? AND type=?", (a, model, t))
            if t == "cartridge":
                c.execute("UPDATE printers SET cartridge_amount=cartridge_amount+? WHERE id=?", (a, pid))
            else:
                c.execute("UPDATE printers SET drum_amount=drum_amount+? WHERE id=?", (a, pid))
            c.execute("SELECT name FROM printers WHERE id=?", (pid,))
            prn_name = c.fetchone()[0]
            c.execute("INSERT INTO storage_transfer_history (datetime, username, model, type, amount, from_place, to_place) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.username, model, t, a, "склад", prn_name))
            conn.commit()
            conn.close()
            self.refresh_storage()
            self.refresh_printers()

    # ========== HISTORY ==========
    def setup_history_tab(self):
        layout = QVBoxLayout(self.tab_history)
        self.history_text = QTextEdit()
        self.history_text.setReadOnly(True)
        layout.addWidget(self.history_text)
        self.btn_refresh_history = QPushButton("Обновить историю")
        layout.addWidget(self.btn_refresh_history)
        self.btn_refresh_history.clicked.connect(self.refresh_history)
        self.refresh_history()

    def refresh_history(self):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT datetime, username, model, type, amount, from_place, to_place FROM storage_transfer_history ORDER BY datetime DESC")
        rows = c.fetchall()
        s = ""
        for dt, user, model, t, amt, ffrom, to in rows:
            s += f"{dt}: {model} [{t}], {amt} шт., {ffrom} → {to} (Оператор: {user})\n"
        self.history_text.setText(s or "История пуста")
        conn.close()

    # ========== ANALYTICS ==========
    def setup_analytics_tab(self):
        layout = QVBoxLayout(self.tab_analytics)
        self.btn_plot_cart = QPushButton("График расхода картриджей")
        self.btn_plot_drum = QPushButton("График расхода драмов")
        self.btn_top5_cart = QPushButton("Топ-5 картриджей")
        self.btn_top5_drum = QPushButton("Топ-5 драмов")
        self.btn_forecast = QPushButton("Прогноз по модели")
        self.btn_export = QPushButton("Экспорт в Excel и PNG")
        layout.addWidget(self.btn_plot_cart)
        layout.addWidget(self.btn_plot_drum)
        layout.addWidget(self.btn_top5_cart)
        layout.addWidget(self.btn_top5_drum)
        layout.addWidget(self.btn_forecast)
        layout.addWidget(self.btn_export)
        layout.addStretch(1)

        self.btn_plot_cart.clicked.connect(analytics.plot_cartridge_usage)
        self.btn_plot_drum.clicked.connect(analytics.plot_drum_usage)
        self.btn_top5_cart.clicked.connect(analytics.top5_cartridge_models)
        self.btn_top5_drum.clicked.connect(analytics.top5_drum_models)
        self.btn_export.clicked.connect(self.export_analytics)
        self.btn_forecast.clicked.connect(self.forecast_dialog)

    def export_analytics(self):
        analytics.export_cartridge_usage_to_excel()
        analytics.export_drum_usage_to_excel()
        analytics.save_cartridge_usage_plot()
        analytics.save_drum_usage_plot()
        QMessageBox.information(self, "Экспорт", "Экспорт выполнен. Смотрите файлы в папке программы.")

    def forecast_dialog(self):
        model, ok = QInputDialog.getText(self, "Прогноз", "Введите модель и тип (через запятую):\nнапример\nCanon 725, cartridge")
        if ok and "," in model:
            m, t = model.split(",", 1)
            t = t.strip()
            m = m.strip()
            if t not in ("cartridge", "drum"):
                QMessageBox.warning(self, "Ошибка", "Тип должен быть cartridge или drum")
                return
            analytics.forecast_next_month(m, t)

    # ========== USERS ==========
    def setup_users_tab(self):
        layout = QVBoxLayout(self.tab_users)
        self.users_list = QListWidget()
        layout.addWidget(self.users_list)
        btns = QHBoxLayout()
        self.btn_add_user = QPushButton("Добавить")
        self.btn_edit_user = QPushButton("Изменить")
        self.btn_del_user = QPushButton("Удалить")
        btns.addWidget(self.btn_add_user)
        btns.addWidget(self.btn_edit_user)
        btns.addWidget(self.btn_del_user)
        layout.addLayout(btns)
        layout.addStretch(1)
        self.btn_add_user.clicked.connect(self.add_user)
        self.btn_edit_user.clicked.connect(self.edit_user)
        self.btn_del_user.clicked.connect(self.delete_user)
        self.refresh_users()

    def refresh_users(self):
        self.users_list.clear()
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT login, role FROM users")
        users = c.fetchall()
        for login, role in users:
            self.users_list.addItem(f"{login} ({role})")
        conn.close()

    def add_user(self):
        dlg = UserDialog(parent=self)
        if dlg.exec():
            login, password, role = dlg.get_data()
            if not login or not password:
                QMessageBox.warning(self, "Ошибка", "Укажите логин и пароль")
                return
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            try:
                c.execute("INSERT INTO users (login, password, role) VALUES (?, ?, ?)",
                          (login, hash_password(password), role))
                conn.commit()
                self.refresh_users()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Ошибка", "Пользователь с таким логином уже существует.")
            conn.close()

    def edit_user(self):
        idx = self.users_list.currentRow()
        if idx < 0:
            return
        login = self.users_list.item(idx).text().split(" ")[0]
        if login == "admin":
            QMessageBox.warning(self, "Ошибка", "Главного администратора нельзя редактировать.")
            return
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT role FROM users WHERE login=?", (login,))
        row = c.fetchone()
        conn.close()
        if not row:
            return
        dlg = UserDialog(login, row[0], self)
        if dlg.exec():
            new_login, password, role = dlg.get_data()
            if not new_login:
                QMessageBox.warning(self, "Ошибка", "Укажите логин")
                return
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            if password:
                c.execute("UPDATE users SET login=?, password=?, role=? WHERE login=?",
                          (new_login, hash_password(password), role, login))
            else:
                c.execute("UPDATE users SET login=?, role=? WHERE login=?",
                          (new_login, role, login))
            conn.commit()
            conn.close()
            self.refresh_users()

    def delete_user(self):
        idx = self.users_list.currentRow()
        if idx < 0:
            return
        login = self.users_list.item(idx).text().split(" ")[0]
        if login == "admin":
            QMessageBox.warning(self, "Ошибка", "Главного администратора нельзя удалить.")
            return
        reply = QMessageBox.question(self, "Удалить пользователя", f"Удалить пользователя '{login}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE login=?", (login,))
            conn.commit()
            conn.close()
            self.refresh_users()

if __name__ == "__main__":
    init_db()
    app = QApplication(sys.argv)
    login_ok = False
    user_role = None
    username = None
    while not login_ok:
        dlg = LoginDialog()
        if not dlg.exec():
            sys.exit(0)
        login, password = dlg.get_credentials()
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT role, password FROM users WHERE login=?", (login,))
        row = c.fetchone()
        conn.close()
        if row and hash_password(password) == row[1]:
            user_role = row[0]
            username = login
            login_ok = True
        else:
            QMessageBox.warning(None, "Ошибка входа", "Неверный логин или пароль")
    win = MainWindow(user_role, username)
    win.show()
    sys.exit(app.exec())