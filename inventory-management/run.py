from app import create_app, db
from app.models import User, UserRole

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User}

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Создаем администратора по умолчанию, если его нет
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@example.com',
                role=UserRole.ADMIN
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Создан администратор по умолчанию: admin / admin123")
    
    app.run(debug=True, host='0.0.0.0', port=5000)