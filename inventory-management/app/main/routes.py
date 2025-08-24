from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.main import bp
from app.auth.routes import operator_required, admin_required
from app.models import (User, Room, Printer, PrinterModel, Supply, Stock, 
                       Movement, History, SupplyType, MovementType)

@bp.route('/')
@bp.route('/index')
@login_required
def index():
    # Собираем статистику для дашборда
    stats = {
        'rooms': Room.query.count(),
        'printers': Printer.query.filter_by(status='active').count(),
        'supplies': Supply.query.count(),
        'stock_available': Stock.query.filter_by(status='available').count(),
        'low_stock_items': sum(1 for s in Supply.query.all() if s.is_low_stock()),
        'recent_movements': Movement.query.order_by(Movement.timestamp.desc()).limit(5).all()
    }
    return render_template('index.html', title='Главная', stats=stats)

@bp.route('/rooms')
@login_required
def rooms():
    rooms = Room.query.all()
    return render_template('rooms/list.html', title='Кабинеты', rooms=rooms)

@bp.route('/rooms/new')
@operator_required
def new_room():
    return render_template('rooms/form.html', title='Новый кабинет')

@bp.route('/printers')
@login_required
def printers():
    printers = Printer.query.all()
    return render_template('printers/list.html', title='Принтеры', printers=printers)

@bp.route('/printers/new')
@operator_required
def new_printer():
    models = PrinterModel.query.all()
    rooms = Room.query.all()
    return render_template('printers/form.html', title='Новый принтер', 
                         models=models, rooms=rooms)

@bp.route('/printers/<int:id>')
@login_required
def printer_detail(id):
    printer = Printer.query.get_or_404(id)
    available_stock = Stock.query.filter_by(status='available').join(Supply).all()
    movements = Movement.query.filter_by(printer_id=id).order_by(Movement.timestamp.desc()).limit(10).all()
    return render_template('printers/detail.html', title=f'Принтер {printer.inventory_number}', 
                         printer=printer, available_stock=available_stock, movements=movements)

@bp.route('/supplies')
@login_required
def supplies():
    supplies = Supply.query.all()
    return render_template('supplies/list.html', title='Расходники', supplies=supplies)

@bp.route('/supplies/new')
@operator_required
def new_supply():
    supply_types = [(t.value, t.value) for t in SupplyType]
    return render_template('supplies/form.html', title='Новый расходник', 
                         supply_types=supply_types)

@bp.route('/stock')
@login_required
def stock():
    stock_items = Stock.query.filter_by(status='available').all()
    return render_template('stock/list.html', title='Склад', stock_items=stock_items)

@bp.route('/stock/receipt')
@operator_required
def stock_receipt():
    supplies = Supply.query.all()
    return render_template('stock/receipt.html', title='Приход на склад', supplies=supplies)

@bp.route('/movements')
@login_required
def movements():
    page = request.args.get('page', 1, type=int)
    movements = Movement.query.order_by(Movement.timestamp.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('movements/list.html', title='История движений', 
                         movements=movements)

@bp.route('/history')
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    history_records = History.query.order_by(History.timestamp.desc()).paginate(
        page=page, per_page=50, error_out=False
    )
    return render_template('history/list.html', title='История операций', 
                         history=history_records)

@bp.route('/users')
@admin_required
def users():
    users = User.query.all()
    return render_template('users/list.html', title='Пользователи', users=users)

@bp.route('/notifications')
@login_required
def notifications():
    low_stock_supplies = [s for s in Supply.query.all() if s.is_low_stock()]
    return render_template('notifications.html', title='Уведомления', 
                         low_stock_supplies=low_stock_supplies)