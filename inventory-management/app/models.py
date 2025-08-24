from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager
from enum import Enum

class UserRole(Enum):
    ADMIN = 'admin'
    OPERATOR = 'operator'
    VIEWER = 'viewer'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.Enum(UserRole), default=UserRole.VIEWER)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    movements = db.relationship('Movement', backref='responsible_user', lazy='dynamic')
    history_records = db.relationship('History', backref='user', lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        return self.role == UserRole.ADMIN
    
    def is_operator(self):
        return self.role in [UserRole.ADMIN, UserRole.OPERATOR]

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100))
    floor = db.Column(db.Integer)
    building = db.Column(db.String(50))
    
    # Связи
    printers = db.relationship('Printer', backref='room', lazy='dynamic')
    
    def __repr__(self):
        return f'<Room {self.number}>'

class PrinterModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    manufacturer = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(100), nullable=False)
    
    # Связи
    printers = db.relationship('Printer', backref='printer_model', lazy='dynamic')
    compatible_supplies = db.relationship('Supply', secondary='printer_model_supply', 
                                        backref=db.backref('compatible_models', lazy='dynamic'))

# Таблица связи для совместимости принтеров и расходников
printer_model_supply = db.Table('printer_model_supply',
    db.Column('printer_model_id', db.Integer, db.ForeignKey('printer_model.id'), primary_key=True),
    db.Column('supply_id', db.Integer, db.ForeignKey('supply.id'), primary_key=True)
)

class Printer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inventory_number = db.Column(db.String(50), unique=True, nullable=False)
    serial_number = db.Column(db.String(100), unique=True)
    model_id = db.Column(db.Integer, db.ForeignKey('printer_model.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    ip_address = db.Column(db.String(15))
    status = db.Column(db.String(20), default='active')  # active, repair, decommissioned
    purchase_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    
    # Текущие установленные расходники
    current_supplies = db.relationship('PrinterSupply', backref='printer', lazy='dynamic')
    
    def __repr__(self):
        return f'<Printer {self.inventory_number}>'

class SupplyType(Enum):
    CARTRIDGE = 'cartridge'
    DRUM = 'drum'
    TONER = 'toner'
    OTHER = 'other'

class Supply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.Enum(SupplyType), nullable=False)
    color = db.Column(db.String(20))  # black, cyan, magenta, yellow
    min_stock = db.Column(db.Integer, default=5)
    
    # Связи
    stock_items = db.relationship('Stock', backref='supply', lazy='dynamic')
    
    def get_current_stock(self):
        return self.stock_items.filter_by(status='available').count()
    
    def is_low_stock(self):
        return self.get_current_stock() <= self.min_stock

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    supply_id = db.Column(db.Integer, db.ForeignKey('supply.id'), nullable=False)
    serial_number = db.Column(db.String(100), unique=True)
    status = db.Column(db.String(20), default='available')  # available, installed, used, defective
    receipt_date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    
    # Связи
    movements = db.relationship('Movement', backref='stock_item', lazy='dynamic')

class PrinterSupply(db.Model):
    """Текущие установленные расходники в принтерах"""
    id = db.Column(db.Integer, primary_key=True)
    printer_id = db.Column(db.Integer, db.ForeignKey('printer.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    installed_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    stock = db.relationship('Stock')

class MovementType(Enum):
    RECEIPT = 'receipt'  # Поступление на склад
    INSTALL = 'install'  # Установка в принтер
    REMOVE = 'remove'   # Снятие с принтера
    DISPOSE = 'dispose'  # Списание
    TRANSFER = 'transfer'  # Перемещение

class Movement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(db.Integer, db.ForeignKey('stock.id'), nullable=False)
    type = db.Column(db.Enum(MovementType), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    printer_id = db.Column(db.Integer, db.ForeignKey('printer.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    
    # Связи
    printer = db.relationship('Printer')

class History(db.Model):
    """История всех операций в системе"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    description = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(15))
    
    def __repr__(self):
        return f'<History {self.action} by {self.user_id} at {self.timestamp}>'