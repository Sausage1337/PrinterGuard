import PyInstaller.__main__

PyInstaller.__main__.run([
    'main.py',  # основной файл вашего проекта
    '--onefile',
    '--windowed',
    '--name=ver1.0.B5',
    '--add-data=office.db;.',  # база данных (для Windows, для Linux замените ; на :)
    '--hidden-import=openpyxl',
    '--hidden-import=xlsxwriter',
    '--hidden-import=matplotlib',
    '--hidden-import=matplotlib.backends.backend_qtagg',
    '--hidden-import=pandas',
    '--hidden-import=numpy',
    '--hidden-import=PySide6.QtCore',
    '--hidden-import=PySide6.QtGui',
    '--hidden-import=PySide6.QtWidgets'
])


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
    c.execute('''SELECT cabinets.name,
                        printers.id,
                        printers.name,
                        printers.cartridge,
                        printers.drum,
                        printers.cartridge_amount,
                        printers.drum_amount,
                        printers.min_cartridge_amount,
                        printers.min_drum_amount
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
    cart_amt = QSpinBox();
    cart_amt.setMaximum(1000)
    drum_amt = QSpinBox();
    drum_amt.setMaximum(1000)
    min_cart = QSpinBox();
    min_cart.setMaximum(100)
    min_drum = QSpinBox();
    min_drum.setMaximum(100)
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
        c.execute('''INSERT INTO printers (cabinet_id, name, cartridge, drum, cartridge_amount, drum_amount,
                                           min_cartridge_amount, min_drum_amount)
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
    cart_amt_spin = QSpinBox();
    cart_amt_spin.setValue(cart_amt);
    cart_amt_spin.setMaximum(1000)
    drum_amt_spin = QSpinBox();
    drum_amt_spin.setValue(drum_amt);
    drum_amt_spin.setMaximum(1000)
    min_cart_spin = QSpinBox();
    min_cart_spin.setValue(min_cart);
    min_cart_spin.setMaximum(100)
    min_drum_spin = QSpinBox();
    min_drum_spin.setValue(min_drum);
    min_drum_spin.setMaximum(100)
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
        c.execute('''UPDATE printers
                     SET cabinet_id=?,
                         name=?,
                         cartridge=?,
                         drum=?,
                         cartridge_amount=?,
                         drum_amount=?,
                         min_cartridge_amount=?,
                         min_drum_amount=?
                     WHERE id = ?''',
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
    reply = QMessageBox.question(self, "Удалить принтер", f"Удалить принтер '{name}'?",
                                 QMessageBox.Yes | QMessageBox.No)
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
    spin_cart = QSpinBox();
    spin_cart.setMaximum(cart_amt);
    spin_cart.setValue(0)
    spin_drum = QSpinBox();
    spin_drum.setMaximum(drum_amt);
    spin_drum.setValue(0)
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
        c.execute(
            "INSERT INTO writeoff_history (printer_id, writeoff_cartridge, writeoff_drum, datetime, username) VALUES (?, ?, ?, ?, ?)",
            (pid, wc, wd, now, self.username))
        conn.commit()
        conn.close()
        self.refresh_printers()
        self.refresh_overview()
