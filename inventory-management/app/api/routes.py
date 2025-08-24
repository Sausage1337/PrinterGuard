from flask import jsonify, request, current_app
from flask_login import login_required, current_user
from app import db
from app.api import bp
from app.auth.routes import operator_required, admin_required
from app.models import (User, Room, Printer, PrinterModel, Supply, Stock, 
                       Movement, History, PrinterSupply, MovementType, SupplyType)
from datetime import datetime

def log_action(action, entity_type=None, entity_id=None, description=None):
    """Вспомогательная функция для логирования действий"""
    history = History(
        user_id=current_user.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
        ip_address=request.remote_addr
    )
    db.session.add(history)

# API для кабинетов
@bp.route('/rooms', methods=['GET'])
@login_required
def get_rooms():
    rooms = Room.query.all()
    return jsonify([{
        'id': r.id,
        'number': r.number,
        'name': r.name,
        'floor': r.floor,
        'building': r.building,
        'printer_count': r.printers.count()
    } for r in rooms])

@bp.route('/rooms', methods=['POST'])
@operator_required
def create_room():
    data = request.get_json()
    room = Room(
        number=data['number'],
        name=data.get('name'),
        floor=data.get('floor'),
        building=data.get('building')
    )
    db.session.add(room)
    log_action('create_room', 'Room', room.id, f'Создан кабинет {room.number}')
    db.session.commit()
    return jsonify({'message': 'Кабинет создан', 'id': room.id}), 201

# API для моделей принтеров
@bp.route('/printer-models', methods=['GET'])
@login_required
def get_printer_models():
    models = PrinterModel.query.all()
    return jsonify([{
        'id': m.id,
        'manufacturer': m.manufacturer,
        'model': m.model,
        'printer_count': m.printers.count()
    } for m in models])

@bp.route('/printer-models', methods=['POST'])
@operator_required
def create_printer_model():
    data = request.get_json()
    model = PrinterModel(
        manufacturer=data['manufacturer'],
        model=data['model']
    )
    db.session.add(model)
    log_action('create_printer_model', 'PrinterModel', model.id, 
               f'Создана модель принтера {model.manufacturer} {model.model}')
    db.session.commit()
    return jsonify({'message': 'Модель принтера создана', 'id': model.id}), 201

# API для принтеров
@bp.route('/printers', methods=['GET'])
@login_required
def get_printers():
    printers = Printer.query.all()
    return jsonify([{
        'id': p.id,
        'inventory_number': p.inventory_number,
        'serial_number': p.serial_number,
        'model': f'{p.printer_model.manufacturer} {p.printer_model.model}',
        'room': p.room.number,
        'ip_address': p.ip_address,
        'status': p.status,
        'supplies': [{
            'id': ps.id,
            'supply': ps.stock.supply.name,
            'installed_date': ps.installed_date.isoformat()
        } for ps in p.current_supplies]
    } for p in printers])

@bp.route('/printers', methods=['POST'])
@operator_required
def create_printer():
    data = request.get_json()
    printer = Printer(
        inventory_number=data['inventory_number'],
        serial_number=data.get('serial_number'),
        model_id=data['model_id'],
        room_id=data['room_id'],
        ip_address=data.get('ip_address'),
        status=data.get('status', 'active'),
        purchase_date=datetime.strptime(data['purchase_date'], '%Y-%m-%d').date() if data.get('purchase_date') else None,
        notes=data.get('notes')
    )
    db.session.add(printer)
    log_action('create_printer', 'Printer', printer.id, 
               f'Создан принтер {printer.inventory_number}')
    db.session.commit()
    return jsonify({'message': 'Принтер создан', 'id': printer.id}), 201

# API для расходников
@bp.route('/supplies', methods=['GET'])
@login_required
def get_supplies():
    supplies = Supply.query.all()
    return jsonify([{
        'id': s.id,
        'code': s.code,
        'name': s.name,
        'type': s.type.value,
        'color': s.color,
        'current_stock': s.get_current_stock(),
        'min_stock': s.min_stock,
        'is_low_stock': s.is_low_stock()
    } for s in supplies])

@bp.route('/supplies', methods=['POST'])
@operator_required
def create_supply():
    data = request.get_json()
    supply = Supply(
        code=data['code'],
        name=data['name'],
        type=SupplyType(data['type']),
        color=data.get('color'),
        min_stock=data.get('min_stock', 5)
    )
    db.session.add(supply)
    log_action('create_supply', 'Supply', supply.id, 
               f'Создан расходник {supply.name}')
    db.session.commit()
    return jsonify({'message': 'Расходник создан', 'id': supply.id}), 201

# API для склада
@bp.route('/stock', methods=['GET'])
@login_required
def get_stock():
    stock = Stock.query.filter_by(status='available').all()
    return jsonify([{
        'id': s.id,
        'supply': s.supply.name,
        'supply_code': s.supply.code,
        'serial_number': s.serial_number,
        'receipt_date': s.receipt_date.isoformat(),
        'notes': s.notes
    } for s in stock])

@bp.route('/stock/receipt', methods=['POST'])
@operator_required
def receipt_stock():
    data = request.get_json()
    items = []
    
    for item_data in data['items']:
        stock = Stock(
            supply_id=item_data['supply_id'],
            serial_number=item_data.get('serial_number'),
            notes=item_data.get('notes')
        )
        db.session.add(stock)
        items.append(stock)
        
        # Создаем движение
        movement = Movement(
            stock_id=stock.id,
            type=MovementType.RECEIPT,
            user_id=current_user.id,
            notes=f"Поступление на склад"
        )
        db.session.add(movement)
    
    log_action('receipt_stock', None, None, 
               f'Поступление на склад: {len(items)} позиций')
    db.session.commit()
    
    return jsonify({
        'message': f'Принято на склад {len(items)} позиций',
        'items': [item.id for item in items]
    }), 201

# API для установки расходника в принтер
@bp.route('/printers/<int:printer_id>/install-supply', methods=['POST'])
@operator_required
def install_supply(printer_id):
    printer = Printer.query.get_or_404(printer_id)
    data = request.get_json()
    stock_id = data['stock_id']
    
    stock = Stock.query.get_or_404(stock_id)
    if stock.status != 'available':
        return jsonify({'error': 'Расходник недоступен'}), 400
    
    # Обновляем статус расходника
    stock.status = 'installed'
    
    # Создаем связь принтер-расходник
    printer_supply = PrinterSupply(
        printer_id=printer_id,
        stock_id=stock_id
    )
    db.session.add(printer_supply)
    
    # Создаем движение
    movement = Movement(
        stock_id=stock_id,
        type=MovementType.INSTALL,
        user_id=current_user.id,
        printer_id=printer_id,
        notes=f"Установлен в принтер {printer.inventory_number}"
    )
    db.session.add(movement)
    
    log_action('install_supply', 'Printer', printer_id, 
               f'Установлен расходник {stock.supply.name} в принтер {printer.inventory_number}')
    db.session.commit()
    
    return jsonify({'message': 'Расходник установлен'}), 200

# API для списания расходника
@bp.route('/stock/<int:stock_id>/dispose', methods=['POST'])
@operator_required
def dispose_stock(stock_id):
    stock = Stock.query.get_or_404(stock_id)
    data = request.get_json()
    
    # Если расходник установлен в принтере, сначала удаляем связь
    if stock.status == 'installed':
        PrinterSupply.query.filter_by(stock_id=stock_id).delete()
    
    stock.status = 'used'
    
    # Создаем движение
    movement = Movement(
        stock_id=stock_id,
        type=MovementType.DISPOSE,
        user_id=current_user.id,
        notes=data.get('reason', 'Списание')
    )
    db.session.add(movement)
    
    log_action('dispose_stock', 'Stock', stock_id, 
               f'Списан расходник {stock.supply.name}')
    db.session.commit()
    
    return jsonify({'message': 'Расходник списан'}), 200

# API для получения истории движений
@bp.route('/movements', methods=['GET'])
@login_required
def get_movements():
    movements = Movement.query.order_by(Movement.timestamp.desc()).limit(100).all()
    return jsonify([{
        'id': m.id,
        'stock': {
            'id': m.stock_item.id,
            'supply_name': m.stock_item.supply.name,
            'serial_number': m.stock_item.serial_number
        },
        'type': m.type.value,
        'user': m.responsible_user.username,
        'printer': m.printer.inventory_number if m.printer else None,
        'timestamp': m.timestamp.isoformat(),
        'notes': m.notes
    } for m in movements])

# API для получения уведомлений о низких остатках
@bp.route('/notifications/low-stock', methods=['GET'])
@login_required
def get_low_stock_notifications():
    low_stock_supplies = Supply.query.all()
    notifications = []
    
    for supply in low_stock_supplies:
        if supply.is_low_stock():
            notifications.append({
                'id': supply.id,
                'code': supply.code,
                'name': supply.name,
                'current_stock': supply.get_current_stock(),
                'min_stock': supply.min_stock,
                'severity': 'critical' if supply.get_current_stock() == 0 else 'warning'
            })
    
    return jsonify(notifications)

# API для получения истории операций
@bp.route('/history', methods=['GET'])
@login_required
def get_history():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    history = History.query.order_by(History.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return jsonify({
        'items': [{
            'id': h.id,
            'user': h.user.username,
            'action': h.action,
            'entity_type': h.entity_type,
            'entity_id': h.entity_id,
            'description': h.description,
            'timestamp': h.timestamp.isoformat(),
            'ip_address': h.ip_address
        } for h in history.items],
        'total': history.total,
        'pages': history.pages,
        'current_page': page
    })