from app import create_app, db
from app.models import User, UserRole, Room, PrinterModel, Supply, SupplyType, Printer, Stock
from datetime import datetime, date

app = create_app()

with app.app_context():
    # Создаем пользователей
    if not User.query.filter_by(username='operator').first():
        operator = User(
            username='operator',
            email='operator@example.com',
            role=UserRole.OPERATOR
        )
        operator.set_password('operator123')
        db.session.add(operator)
    
    if not User.query.filter_by(username='viewer').first():
        viewer = User(
            username='viewer',
            email='viewer@example.com',
            role=UserRole.VIEWER
        )
        viewer.set_password('viewer123')
        db.session.add(viewer)
    
    # Создаем кабинеты
    rooms = [
        {'number': '101', 'name': 'Бухгалтерия', 'floor': 1, 'building': 'Главный корпус'},
        {'number': '205', 'name': 'IT отдел', 'floor': 2, 'building': 'Главный корпус'},
        {'number': '310', 'name': 'Администрация', 'floor': 3, 'building': 'Главный корпус'},
        {'number': '112', 'name': 'Отдел кадров', 'floor': 1, 'building': 'Главный корпус'},
    ]
    
    for room_data in rooms:
        if not Room.query.filter_by(number=room_data['number']).first():
            room = Room(**room_data)
            db.session.add(room)
    
    # Создаем модели принтеров
    printer_models = [
        {'manufacturer': 'HP', 'model': 'LaserJet P1102'},
        {'manufacturer': 'HP', 'model': 'LaserJet Pro M428fdw'},
        {'manufacturer': 'Canon', 'model': 'i-SENSYS LBP6030B'},
        {'manufacturer': 'Epson', 'model': 'L3150'},
    ]
    
    for model_data in printer_models:
        if not PrinterModel.query.filter_by(manufacturer=model_data['manufacturer'], 
                                          model=model_data['model']).first():
            model = PrinterModel(**model_data)
            db.session.add(model)
    
    # Создаем расходники
    supplies = [
        {'code': 'CE285A', 'name': 'HP 85A Black', 'type': SupplyType.CARTRIDGE, 'color': 'black', 'min_stock': 3},
        {'code': 'CF283A', 'name': 'HP 83A Black', 'type': SupplyType.CARTRIDGE, 'color': 'black', 'min_stock': 3},
        {'code': 'CRG-725', 'name': 'Canon 725 Black', 'type': SupplyType.CARTRIDGE, 'color': 'black', 'min_stock': 2},
        {'code': 'T6641', 'name': 'Epson T6641 Black', 'type': SupplyType.TONER, 'color': 'black', 'min_stock': 4},
        {'code': 'T6642', 'name': 'Epson T6642 Cyan', 'type': SupplyType.TONER, 'color': 'cyan', 'min_stock': 2},
        {'code': 'T6643', 'name': 'Epson T6643 Magenta', 'type': SupplyType.TONER, 'color': 'magenta', 'min_stock': 2},
        {'code': 'T6644', 'name': 'Epson T6644 Yellow', 'type': SupplyType.TONER, 'color': 'yellow', 'min_stock': 2},
    ]
    
    for supply_data in supplies:
        if not Supply.query.filter_by(code=supply_data['code']).first():
            supply = Supply(**supply_data)
            db.session.add(supply)
    
    db.session.commit()
    
    # Создаем принтеры
    room1 = Room.query.filter_by(number='101').first()
    room2 = Room.query.filter_by(number='205').first()
    room3 = Room.query.filter_by(number='310').first()
    
    hp_model1 = PrinterModel.query.filter_by(model='LaserJet P1102').first()
    hp_model2 = PrinterModel.query.filter_by(model='LaserJet Pro M428fdw').first()
    canon_model = PrinterModel.query.filter_by(model='i-SENSYS LBP6030B').first()
    
    printers = [
        {
            'inventory_number': 'PR-001',
            'serial_number': 'VNC3K47890',
            'model_id': hp_model1.id,
            'room_id': room1.id,
            'ip_address': '192.168.1.50',
            'status': 'active',
            'purchase_date': date(2022, 3, 15)
        },
        {
            'inventory_number': 'PR-002',
            'serial_number': 'VND4L23456',
            'model_id': hp_model2.id,
            'room_id': room2.id,
            'ip_address': '192.168.1.51',
            'status': 'active',
            'purchase_date': date(2023, 1, 10)
        },
        {
            'inventory_number': 'PR-003',
            'serial_number': 'CAN789012',
            'model_id': canon_model.id,
            'room_id': room3.id,
            'ip_address': '192.168.1.52',
            'status': 'active',
            'purchase_date': date(2022, 11, 20)
        },
    ]
    
    for printer_data in printers:
        if not Printer.query.filter_by(inventory_number=printer_data['inventory_number']).first():
            printer = Printer(**printer_data)
            db.session.add(printer)
    
    # Создаем складские запасы
    ce285a = Supply.query.filter_by(code='CE285A').first()
    cf283a = Supply.query.filter_by(code='CF283A').first()
    crg725 = Supply.query.filter_by(code='CRG-725').first()
    
    # Добавляем несколько картриджей на склад
    for i in range(5):
        stock = Stock(
            supply_id=ce285a.id,
            serial_number=f'HP85A-2024-{i+1:03d}',
            status='available'
        )
        db.session.add(stock)
    
    for i in range(2):  # Мало CF283A - будет уведомление
        stock = Stock(
            supply_id=cf283a.id,
            serial_number=f'HP83A-2024-{i+1:03d}',
            status='available'
        )
        db.session.add(stock)
    
    for i in range(4):
        stock = Stock(
            supply_id=crg725.id,
            serial_number=f'CRG725-2024-{i+1:03d}',
            status='available'
        )
        db.session.add(stock)
    
    db.session.commit()
    
    print("Демонстрационные данные успешно созданы!")
    print("\nДоступные пользователи:")
    print("1. admin / admin123 (Администратор)")
    print("2. operator / operator123 (Оператор)")
    print("3. viewer / viewer123 (Просмотр)")
    print("\nСоздано:")
    print(f"- {Room.query.count()} кабинетов")
    print(f"- {PrinterModel.query.count()} моделей принтеров")
    print(f"- {Printer.query.count()} принтеров")
    print(f"- {Supply.query.count()} типов расходников")
    print(f"- {Stock.query.filter_by(status='available').count()} единиц на складе")