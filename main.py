import sys
import sqlite3
import hashlib
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QInputDialog, QMessageBox, QLabel, QDialog, QFormLayout,
    QLineEdit, QSpinBox, QDialogButtonBox, QCheckBox, QTextEdit, QComboBox, QListWidgetItem
)
from PySide6.QtGui import QColor
import autoupdate

DB_FILE = "office.db"

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Пользователи
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
    # Кабинеты, принтеры, история списаний
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
    # Склад
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
    # Миграции для новых полей
    c.execute("PRAGMA table_info(writeoff_history)")
    columns = [row[1] for row in c.fetchall()]
    if 'username' not in columns:
        c.execute("ALTER TABLE writeoff_history ADD COLUMN username TEXT")
    c.execute("PRAGMA table_info(printers)")
    columns = [row[1] for row in c.fetchall()]
    if 'min_cartridge_amount' not in columns:
        c.execute("ALTER TABLE printers ADD COLUMN min_cartridge_amount INTEGER DEFAULT 0")
    if 'min_drum_amount' not in columns:
        c.execute("ALTER TABLE printers ADD COLUMN min_drum_amount INTEGER DEFAULT 0")
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

class UserManagementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Управление пользователями")
        self.resize(350, 250)
        layout = QVBoxLayout(self)
        self.user_list = QListWidget()
        self.load_users()
        layout.addWidget(self.user_list)

        btn_add = QPushButton("Добавить пользователя")
        btn_del = QPushButton("Удалить пользователя")
        btn_add.clicked.connect(self.add_user)
        btn_del.clicked.connect(self.delete_user)
        layout.addWidget(btn_add)
        layout.addWidget(btn_del)
        self.setLayout(layout)

    def load_users(self):
        self.user_list.clear()
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT login, role FROM users ORDER BY login")
        for login, role in c.fetchall():
            self.user_list.addItem(f"{login} ({role})")
        conn.close()

    def add_user(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Добавить пользователя")
        form = QFormLayout(dlg)
        login = QLineEdit()
        password = QLineEdit()
        password.setEchoMode(QLineEdit.Password)
        role = QComboBox()
        role.addItems(["admin", "operator", "viewer"])
        form.addRow("Логин:", login)
        form.addRow("Пароль:", password)
        form.addRow("Роль:", role)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        form.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        if dlg.exec():
            l = login.text()
            p = password.text()
            r = role.currentText()
            if not l or not p:
                QMessageBox.warning(self, "Ошибка", "Укажите логин и пароль")
                return
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            try:
                c.execute("INSERT INTO users (login, password, role) VALUES (?, ?, ?)",
                          (l, hash_password(p), r))
                conn.commit()
                self.load_users()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Ошибка", "Пользователь с таким логином уже существует.")
            conn.close()

    def delete_user(self):
        idx = self.user_list.currentRow()
        if idx < 0:
            return
        login = self.user_list.item(idx).text().split(" ")[0]
        if login == "admin":
            QMessageBox.warning(self, "Ошибка", "Нельзя удалить главного администратора.")
            return
        reply = QMessageBox.question(self, "Удалить пользователя", f"Удалить пользователя '{login}'?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE login=?", (login,))
            conn.commit()
            conn.close()
            self.load_users()

class PrinterEditDialog(QDialog):
    def __init__(self, name="", cartridge="", cartridge_amount=0, drum="", drum_amount=0,
                 min_cart_amt=0, min_drum_amt=0, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактировать принтер")
        layout = QFormLayout(self)

        self.name_edit = QLineEdit(name)
        self.cart_edit = QLineEdit(cartridge)
        self.cart_amt = QSpinBox()
        self.cart_amt.setMinimum(0)
        self.cart_amt.setValue(cartridge_amount)
        self.drum_edit = QLineEdit(drum)
        self.drum_amt = QSpinBox()
        self.drum_amt.setMinimum(0)
        self.drum_amt.setValue(drum_amount)
        self.min_cart_amt = QSpinBox()
        self.min_cart_amt.setMinimum(0)
        self.min_cart_amt.setValue(min_cart_amt)
        self.min_drum_amt = QSpinBox()
        self.min_drum_amt.setMinimum(0)
        self.min_drum_amt.setValue(min_drum_amt)

        layout.addRow("Название принтера:", self.name_edit)
        layout.addRow("Модель картриджа:", self.cart_edit)
        layout.addRow("Количество картриджей:", self.cart_amt)
        layout.addRow("Мин. остаток картриджей для напоминания:", self.min_cart_amt)
        layout.addRow("Модель драма:", self.drum_edit)
        layout.addRow("Количество драмов:", self.drum_amt)
        layout.addRow("Мин. остаток драмов для напоминания:", self.min_drum_amt)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        return (
            self.name_edit.text(),
            self.cart_edit.text(),
            self.cart_amt.value(),
            self.drum_edit.text(),
            self.drum_amt.value(),
            self.min_cart_amt.value(),
            self.min_drum_amt.value()
        )

class WriteOffDialog(QDialog):
    def __init__(self, cartridge_amount, drum_amount, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Списать картридж/драм")
        layout = QFormLayout(self)

        self.cb_cart = QCheckBox("Списать картриджи")
        self.cb_drum = QCheckBox("Списать драм")
        self.spin_cart = QSpinBox()
        self.spin_cart.setMinimum(1)
        self.spin_cart.setMaximum(cartridge_amount)
        self.spin_cart.setValue(1)
        self.spin_cart.setEnabled(False)
        self.spin_drum = QSpinBox()
        self.spin_drum.setMinimum(1)
        self.spin_drum.setMaximum(drum_amount)
        self.spin_drum.setValue(1)
        self.spin_drum.setEnabled(False)

        self.cb_cart.toggled.connect(lambda v: self.spin_cart.setEnabled(v))
        self.cb_drum.toggled.connect(lambda v: self.spin_drum.setEnabled(v))

        layout.addRow(self.cb_cart, self.spin_cart)
        layout.addRow(self.cb_drum, self.spin_drum)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if cartridge_amount == 0:
            self.cb_cart.setEnabled(False)
            self.spin_cart.setEnabled(False)
        if drum_amount == 0:
            self.cb_drum.setEnabled(False)
            self.spin_drum.setEnabled(False)

        self.setLayout(layout)

    def get_writeoff(self):
        cart_count = self.spin_cart.value() if self.cb_cart.isChecked() else 0
        drum_count = self.spin_drum.value() if self.cb_drum.isChecked() else 0
        return cart_count, drum_count

class WriteoffHistoryDialog(QDialog):
    def __init__(self, printer_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle("История списаний")
        self.resize(400, 300)
        layout = QVBoxLayout(self)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        layout.addWidget(self.text)
        self.load_history(printer_id)

    def load_history(self, printer_id):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
            SELECT datetime, writeoff_cartridge, writeoff_drum, username
            FROM writeoff_history
            WHERE printer_id=?
            ORDER BY datetime DESC
        """, (printer_id,))
        rows = c.fetchall()
        conn.close()
        if not rows:
            self.text.setText("История списаний пуста.")
            return
        s = ""
        for dt, wc, wd, who in rows:
            parts = []
            if wc:
                parts.append(f"Картриджей: {wc}")
            if wd:
                parts.append(f"Драмов: {wd}")
            who_str = f" (Списал: {who})" if who else ""
            s += f"{dt}: " + ", ".join(parts) + who_str + "\n"
        self.text.setText(s)

class StorageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Склад расходников")
        self.resize(550, 350)
        self.table = QListWidget()
        self.reload_storage()
        btn_add = QPushButton("Пополнить склад")
        btn_transfer = QPushButton("Выдать на принтер")
        btn_return = QPushButton("Вернуть на склад")
        btn_history = QPushButton("История перемещений")

        btn_add.clicked.connect(self.add_to_storage)
        btn_transfer.clicked.connect(self.transfer_to_printer)
        btn_return.clicked.connect(self.return_to_storage)
        btn_history.clicked.connect(self.show_history)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Остатки на складе:"))
        layout.addWidget(self.table)
        h = QHBoxLayout()
        h.addWidget(btn_add)
        h.addWidget(btn_transfer)
        h.addWidget(btn_return)
        h.addWidget(btn_history)
        layout.addLayout(h)
        self.setLayout(layout)

    def reload_storage(self):
        self.table.clear()
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT model, type, amount FROM storage ORDER BY type, model")
        for model, t, amt in c.fetchall():
            self.table.addItem(f"{model} [{t}] — {amt} шт.")
        conn.close()

    def add_to_storage(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Пополнить склад")
        f = QFormLayout(dlg)
        model = QLineEdit()
        t = QComboBox()
        t.addItems(["cartridge", "drum"])
        amount = QSpinBox()
        amount.setMinimum(1)
        f.addRow("Модель:", model)
        f.addRow("Тип:", t)
        f.addRow("Количество:", amount)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        f.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec():
            m = model.text()
            ty = t.currentText()
            amt = amount.value()
            if not m:
                QMessageBox.warning(self, "Ошибка", "Укажите модель!")
                return
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("SELECT id FROM storage WHERE model=? AND type=?", (m, ty))
            row = c.fetchone()
            if row:
                c.execute("UPDATE storage SET amount=amount+? WHERE id=?", (amt, row[0]))
            else:
                c.execute("INSERT INTO storage (model, type, amount) VALUES (?, ?, ?)", (m, ty, amt))
            # Лог в историю
            c.execute("INSERT INTO storage_transfer_history (datetime, username, model, type, amount, from_place, to_place) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.parent().username, m, ty, amt, "внешние поставки", "склад"))
            conn.commit()
            conn.close()
            self.reload_storage()

    def transfer_to_printer(self):
        idx = self.table.currentRow()
        if idx < 0:
            QMessageBox.information(self, "Склад", "Выберите модель для выдачи.")
            return
        item = self.table.item(idx).text()
        parts = item.split(" — ")[0].split(" [")
        model = parts[0].strip()
        t = parts[1][:-1]
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT amount FROM storage WHERE model=? AND type=?", (model, t))
        amount_on_storage = c.fetchone()[0]
        # Список принтеров, куда можно выдать такой расходник
        if t == "cartridge":
            c.execute("SELECT id, name FROM printers WHERE cartridge=?", (model,))
        else:
            c.execute("SELECT id, name FROM printers WHERE drum=?", (model,))
        prns = c.fetchall()
        conn.close()
        if not prns:
            QMessageBox.warning(self, "Нет принтеров", f"Нет принтеров, использующих {model} [{t}]")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Выдать на принтер")
        f = QFormLayout(dlg)
        cb = QComboBox()
        for pid, n in prns:
            cb.addItem(n, pid)
        amt = QSpinBox()
        amt.setMaximum(amount_on_storage)
        amt.setMinimum(1)
        amt.setValue(1)
        f.addRow("Принтер:", cb)
        f.addRow("Количество:", amt)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        f.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec():
            pid = cb.currentData()
            give_amt = amt.value()
            # Перемещаем со склада на принтер
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute("UPDATE storage SET amount=amount-? WHERE model=? AND type=?", (give_amt, model, t))
            if t == "cartridge":
                c.execute("UPDATE printers SET cartridge_amount=cartridge_amount+? WHERE id=?", (give_amt, pid))
            else:
                c.execute("UPDATE printers SET drum_amount=drum_amount+? WHERE id=?", (give_amt, pid))
            # История
            c.execute("SELECT name FROM printers WHERE id=?", (pid,))
            printer_name = c.fetchone()[0]
            c.execute("INSERT INTO storage_transfer_history (datetime, username, model, type, amount, from_place, to_place) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.parent().username, model, t, give_amt, "склад", printer_name))
            conn.commit()
            conn.close()
            self.reload_storage()

    def return_to_storage(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Вернуть на склад")
        f = QFormLayout(dlg)
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, name, cartridge, cartridge_amount, drum, drum_amount FROM printers")
        all_printers = c.fetchall()
        prn_cb = QComboBox()
        for pid, name, cart, cart_amt, drum, drum_amt in all_printers:
            if cart and cart_amt > 0:
                prn_cb.addItem(f"{name}: {cart} (картриджи, {cart_amt} шт.)", (pid, "cartridge", cart, cart_amt))
            if drum and drum_amt > 0:
                prn_cb.addItem(f"{name}: {drum} (драмы, {drum_amt} шт.)", (pid, "drum", drum, drum_amt))
        conn.close()
        if prn_cb.count() == 0:
            QMessageBox.information(self, "Нет расходников", "Нет расходников для возврата на склад.")
            return
        amt = QSpinBox()
        amt.setMinimum(1)
        amt.setMaximum(prn_cb.currentData()[3])
        amt.setValue(1)
        def update_amt(idx):
            amt.setMaximum(prn_cb.itemData(idx)[3])
        prn_cb.currentIndexChanged.connect(update_amt)
        f.addRow("Принтер/расходник:", prn_cb)
        f.addRow("Количество для возврата:", amt)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        f.addWidget(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        if dlg.exec():
            pid, t, model, max_amt = prn_cb.currentData()
            amount = amt.value()
            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            # Уменьшаем у принтера, увеличиваем на складе
            if t == "cartridge":
                c.execute("UPDATE printers SET cartridge_amount=cartridge_amount-? WHERE id=?", (amount, pid))
            else:
                c.execute("UPDATE printers SET drum_amount=drum_amount-? WHERE id=?", (amount, pid))
            c.execute("SELECT id FROM storage WHERE model=? AND type=?", (model, t))
            storage_row = c.fetchone()
            if storage_row:
                c.execute("UPDATE storage SET amount=amount+? WHERE id=?", (amount, storage_row[0]))
            else:
                c.execute("INSERT INTO storage (model, type, amount) VALUES (?, ?, ?)", (model, t, amount))
            # История
            c.execute("SELECT name FROM printers WHERE id=?", (pid,))
            printer_name = c.fetchone()[0]
            c.execute("INSERT INTO storage_transfer_history (datetime, username, model, type, amount, from_place, to_place) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), self.parent().username, model, t, amount, printer_name, "склад"))
            conn.commit()
            conn.close()
            self.reload_storage()

    def show_history(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("История перемещений склада")
        dlg.resize(600,350)
        text = QTextEdit()
        text.setReadOnly(True)
        layout = QVBoxLayout(dlg)
        layout.addWidget(text)
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT datetime, username, model, type, amount, from_place, to_place FROM storage_transfer_history ORDER BY datetime DESC")
        rows = c.fetchall()
        conn.close()
        s = ""
        for dt, user, model, t, amt, ffrom, to in rows:
            s += f"{dt}: {model} [{t}], {amt} шт., {ffrom} → {to} (Оператор: {user})\n"
        text.setText(s or "История пуста")
        dlg.exec()

class MainWindow(QWidget):
    def __init__(self, user_role, username, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Учёт кабинетов и принтеров (PySide6)")
        self.resize(920, 400)
        self.cabinets = []
        self.printers = []
        self.user_role = user_role
        self.username = username

        main_layout = QHBoxLayout(self)
        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()

        self.cabinet_list = QListWidget()
        self.cabinet_list.currentRowChanged.connect(self.on_cabinet_selected)
        self.printer_list = QListWidget()
        self.printer_list.currentRowChanged.connect(self.on_printer_selected)
        self.printer_list.itemDoubleClicked.connect(self.edit_printer)

        self.btn_add_cab = QPushButton("Добавить кабинет")
        self.btn_del_cab = QPushButton("Удалить кабинет")
        self.btn_add_prn = QPushButton("Добавить принтер")
        self.btn_del_prn = QPushButton("Удалить принтер")
        self.btn_edit_prn = QPushButton("Редактировать принтер")
        self.btn_writeoff = QPushButton("Списать картридж/драм")
        self.btn_history = QPushButton("История списаний")
        self.btn_users = QPushButton("Пользователи")
        self.btn_storage = QPushButton("Склад расходников")
        self.btn_update = QPushButton("Обновление")
        self.btn_update.clicked.connect(self.do_update)

        self.btn_add_cab.clicked.connect(self.add_cabinet)
        self.btn_del_cab.clicked.connect(self.delete_cabinet)
        self.btn_add_prn.clicked.connect(self.add_printer)
        self.btn_del_prn.clicked.connect(self.delete_printer)
        self.btn_edit_prn.clicked.connect(self.edit_printer)
        self.btn_writeoff.clicked.connect(self.writeoff_items)
        self.btn_history.clicked.connect(self.show_writeoff_history)
        self.btn_users.clicked.connect(self.manage_users)
        self.btn_storage.clicked.connect(self.open_storage)

        self.info_label = QLabel("Выберите кабинет и принтер для просмотра информации.")

        left_layout.addWidget(QLabel("Кабинеты:"))
        left_layout.addWidget(self.cabinet_list)
        left_layout.addWidget(self.btn_add_cab)
        left_layout.addWidget(self.btn_del_cab)
        left_layout.addWidget(self.btn_storage)
        left_layout.addWidget(self.btn_update)
        if self.user_role == "admin":
            left_layout.addWidget(self.btn_users)

        right_layout.addWidget(QLabel("Принтеры выбранного кабинета:"))
        right_layout.addWidget(self.printer_list)
        right_layout.addWidget(self.btn_add_prn)
        right_layout.addWidget(self.btn_del_prn)
        right_layout.addWidget(self.btn_edit_prn)
        right_layout.addWidget(self.btn_writeoff)
        right_layout.addWidget(self.btn_history)
        right_layout.addWidget(self.info_label)

        main_layout.addLayout(left_layout, 1)
        main_layout.addLayout(right_layout, 2)
        self.setLayout(main_layout)
        self.update_role_permissions()
        self.load_cabinets()

    def do_update(self):
        autoupdate.check_and_update_gui(self)

    def update_role_permissions(self):
        if self.user_role == "admin":
            pass
        elif self.user_role == "operator":
            self.btn_del_cab.setEnabled(False)
            self.btn_users.setEnabled(False)
        elif self.user_role == "viewer":
            self.btn_add_cab.setEnabled(False)
            self.btn_del_cab.setEnabled(False)
            self.btn_add_prn.setEnabled(False)
            self.btn_del_prn.setEnabled(False)
            self.btn_edit_prn.setEnabled(False)
            self.btn_writeoff.setEnabled(False)
            self.btn_users.setEnabled(False)
            self.btn_storage.setEnabled(False)
            self.btn_update.setEnabled(False)

    def db_conn(self):
        return sqlite3.connect(DB_FILE)

    def load_cabinets(self):
        self.cabinet_list.clear()
        conn = self.db_conn()
        c = conn.cursor()
        c.execute("SELECT id, name FROM cabinets ORDER BY name")
        self.cabinets = c.fetchall()
        for _id, name in self.cabinets:
            self.cabinet_list.addItem(name)
        conn.close()
        self.printer_list.clear()
        self.info_label.setText("Выберите кабинет и принтер для просмотра информации.")

    def check_low_stock(self, printers=None):
        if printers is None:
            conn = self.db_conn()
            c = conn.cursor()
            c.execute('''
                SELECT cabinets.name, printers.name, cartridge_amount, min_cartridge_amount, drum_amount, min_drum_amount
                FROM printers
                LEFT JOIN cabinets ON printers.cabinet_id = cabinets.id
            ''')
            printers = c.fetchall()
            conn.close()
        messages = []
        for cab, prn, cart_amt, min_cart, drum_amt, min_drum in printers:
            if min_cart > 0 and cart_amt <= min_cart:
                messages.append(f"ВНИМАНИЕ: В кабинете '{cab}' у принтера '{prn}' мало картриджей ({cart_amt} ≤ {min_cart})")
            if min_drum > 0 and drum_amt <= min_drum:
                messages.append(f"ВНИМАНИЕ: В кабинете '{cab}' у принтера '{prn}' мало драмов ({drum_amt} ≤ {min_drum})")
        if messages:
            QMessageBox.warning(self, "Низкий остаток", "\n".join(messages))

    def on_cabinet_selected(self, idx):
        self.printer_list.clear()
        self.info_label.setText("Выберите принтер для просмотра информации.")
        if idx < 0 or idx >= len(self.cabinets):
            return
        cabinet_id = self.cabinets[idx][0]
        conn = self.db_conn()
        c = conn.cursor()
        c.execute("""
            SELECT id, name, cartridge, drum, cartridge_amount, drum_amount, min_cartridge_amount, min_drum_amount
            FROM printers WHERE cabinet_id=? ORDER BY name
        """, (cabinet_id,))
        self.printers = c.fetchall()
        for _id, name, cartridge, drum, cart_amt, drum_amt, min_cart, min_drum in self.printers:
            warning = False
            tail = ""
            if min_cart > 0 and cart_amt <= min_cart:
                tail += " [Мало картриджей!]"
                warning = True
            if min_drum > 0 and drum_amt <= min_drum:
                tail += " [Мало драмов!]"
                warning = True
            label = f"{name} | Картридж: {cartridge or '-'} ({cart_amt}), Драм: {drum or '-'} ({drum_amt}){tail}"
            if warning:
                label = "⚠️ " + label
            item = QListWidgetItem(label)
            if warning:
                item.setBackground(QColor(255, 255, 128))
            self.printer_list.addItem(item)
        self.check_low_stock(
            [(self.cabinets[idx][1], name, cart_amt, min_cart, drum_amt, min_drum)
             for _id, name, cartridge, drum, cart_amt, drum_amt, min_cart, min_drum in self.printers]
        )
        conn.close()

    def on_printer_selected(self, idx):
        if idx < 0 or idx >= len(self.printers):
            self.info_label.setText("Выберите принтер для просмотра информации.")
            return
        _id, name, cartridge, drum, cart_amt, drum_amt, min_cart, min_drum = self.printers[idx]
        info = (
            f"<b>Принтер:</b> {name}<br>"
            f"<b>Картридж:</b> {cartridge or '-'}<br>"
            f"<b>Количество картриджей:</b> {cart_amt} (мин. {min_cart})<br>"
            f"<b>Драм:</b> {drum or '-'}<br>"
            f"<b>Количество драмов:</b> {drum_amt} (мин. {min_drum})"
        )
        self.info_label.setText(info)

    def add_cabinet(self):
        name, ok = QInputDialog.getText(self, "Добавить кабинет", "Название кабинета:")
        if ok and name:
            try:
                conn = self.db_conn()
                c = conn.cursor()
                c.execute("INSERT INTO cabinets (name) VALUES (?)", (name,))
                conn.commit()
                conn.close()
                self.load_cabinets()
            except sqlite3.IntegrityError:
                QMessageBox.warning(self, "Ошибка", "Кабинет с таким названием уже существует!")

    def delete_cabinet(self):
        idx = self.cabinet_list.currentRow()
        if idx < 0 or idx >= len(self.cabinets):
            return
        cabinet_id, name = self.cabinets[idx]
        reply = QMessageBox.question(self, "Удалить кабинет",
                                     f"Удалить кабинет '{name}' и все его принтеры?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            conn = self.db_conn()
            c = conn.cursor()
            c.execute("DELETE FROM printers WHERE cabinet_id=?", (cabinet_id,))
            c.execute("DELETE FROM cabinets WHERE id=?", (cabinet_id,))
            conn.commit()
            conn.close()
            self.load_cabinets()

    def add_printer(self):
        cidx = self.cabinet_list.currentRow()
        if cidx < 0 or cidx >= len(self.cabinets):
            return
        cabinet_id = self.cabinets[cidx][0]
        dialog = PrinterEditDialog(parent=self)
        if dialog.exec():
            name, cartridge, cart_amt, drum, drum_amt, min_cart, min_drum = dialog.get_data()
            if not name:
                QMessageBox.warning(self, "Ошибка", "Название принтера не может быть пустым!")
                return
            conn = self.db_conn()
            c = conn.cursor()
            c.execute("""
                INSERT INTO printers (cabinet_id, name, cartridge, drum, cartridge_amount, drum_amount, min_cartridge_amount, min_drum_amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (cabinet_id, name, cartridge, drum, cart_amt, drum_amt, min_cart, min_drum))
            conn.commit()
            conn.close()
            self.on_cabinet_selected(cidx)

    def delete_printer(self):
        cidx = self.cabinet_list.currentRow()
        pidx = self.printer_list.currentRow()
        if pidx < 0 or pidx >= len(self.printers):
            return
        printer_id, name, *_ = self.printers[pidx]
        reply = QMessageBox.question(self, "Удалить принтер",
                                     f"Удалить принтер '{name}'?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            conn = self.db_conn()
            c = conn.cursor()
            c.execute("DELETE FROM printers WHERE id=?", (printer_id,))
            conn.commit()
            conn.close()
            self.on_cabinet_selected(cidx)

    def edit_printer(self):
        cidx = self.cabinet_list.currentRow()
        pidx = self.printer_list.currentRow()
        if pidx < 0 or pidx >= len(self.printers):
            return
        printer = self.printers[pidx]
        (printer_id, name, cartridge, drum, cart_amt, drum_amt, min_cart, min_drum) = printer
        dialog = PrinterEditDialog(
            name=name,
            cartridge=cartridge or "",
            cartridge_amount=cart_amt,
            drum=drum or "",
            drum_amount=drum_amt,
            min_cart_amt=min_cart,
            min_drum_amt=min_drum,
            parent=self
        )
        if dialog.exec():
            new_name, new_cartridge, new_cart_amt, new_drum, new_drum_amt, new_min_cart, new_min_drum = dialog.get_data()
            if not new_name:
                QMessageBox.warning(self, "Ошибка", "Название принтера не может быть пустым!")
                return
            conn = self.db_conn()
            c = conn.cursor()
            c.execute("""
                UPDATE printers
                SET name=?, cartridge=?, cartridge_amount=?, drum=?, drum_amount=?, min_cartridge_amount=?, min_drum_amount=?
                WHERE id=?""",
                (new_name, new_cartridge, new_cart_amt, new_drum, new_drum_amt, new_min_cart, new_min_drum, printer_id))
            conn.commit()
            conn.close()
            self.on_cabinet_selected(cidx)

    def writeoff_items(self):
        cidx = self.cabinet_list.currentRow()
        pidx = self.printer_list.currentRow()
        if pidx < 0 or pidx >= len(self.printers):
            return
        printer = self.printers[pidx]
        printer_id, name, cartridge, drum, cart_amt, drum_amt, min_cart, min_drum = printer
        if cart_amt == 0 and drum_amt == 0:
            QMessageBox.information(self, "Нет в наличии", "Нет картриджей и драмов на списание для этого принтера.")
            return
        dialog = WriteOffDialog(cart_amt, drum_amt, self)
        if dialog.exec():
            writeoff_cart, writeoff_drum = dialog.get_writeoff()
            if writeoff_cart == 0 and writeoff_drum == 0:
                return
            if writeoff_cart > cart_amt or writeoff_drum > drum_amt:
                QMessageBox.warning(self, "Ошибка", "Нельзя списать больше, чем есть в наличии.")
                return
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = self.db_conn()
            c = conn.cursor()
            c.execute("""
                UPDATE printers
                SET cartridge_amount=cartridge_amount-?, drum_amount=drum_amount-?
                WHERE id=?""", (writeoff_cart, writeoff_drum, printer_id))
            c.execute("""
                INSERT INTO writeoff_history (printer_id, writeoff_cartridge, writeoff_drum, datetime, username)
                VALUES (?, ?, ?, ?, ?)""",
                (printer_id, writeoff_cart, writeoff_drum, now, self.username))
            conn.commit()
            conn.close()
            self.on_cabinet_selected(cidx)
            QMessageBox.information(self, "Списание", f"Списано:\nКартриджей: {writeoff_cart}\nДрамов: {writeoff_drum}")

    def show_writeoff_history(self):
        pidx = self.printer_list.currentRow()
        if pidx < 0 or pidx >= len(self.printers):
            QMessageBox.information(self, "История", "Выберите принтер.")
            return
        printer_id = self.printers[pidx][0]
        dialog = WriteoffHistoryDialog(printer_id, self)
        dialog.exec()

    def manage_users(self):
        dlg = UserManagementDialog(self)
        dlg.exec()

    def open_storage(self):
        dlg = StorageDialog(self)
        dlg.exec()

if __name__ == "__main__":
    init_db()
    app = QApplication(sys.argv)
    # Авторизация
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