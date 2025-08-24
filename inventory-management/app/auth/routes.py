from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm
from app.models import User, UserRole, History
from functools import wraps

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin():
            flash('У вас нет прав для выполнения этого действия.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

def operator_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_operator():
            flash('У вас нет прав для выполнения этого действия.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Неверное имя пользователя или пароль', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=form.remember_me.data)
        
        # Запись в историю
        history = History(
            user_id=user.id,
            action='login',
            description=f'Пользователь {user.username} вошел в систему',
            ip_address=request.remote_addr
        )
        db.session.add(history)
        db.session.commit()
        
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('main.index')
        return redirect(next_page)
    
    return render_template('auth/login.html', title='Вход', form=form)

@bp.route('/logout')
def logout():
    if current_user.is_authenticated:
        # Запись в историю
        history = History(
            user_id=current_user.id,
            action='logout',
            description=f'Пользователь {current_user.username} вышел из системы',
            ip_address=request.remote_addr
        )
        db.session.add(history)
        db.session.commit()
    
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/register', methods=['GET', 'POST'])
@admin_required
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            role=UserRole(form.role.data)
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        # Запись в историю
        history = History(
            user_id=current_user.id,
            action='create_user',
            entity_type='User',
            entity_id=user.id,
            description=f'Создан пользователь {user.username} с ролью {user.role.value}',
            ip_address=request.remote_addr
        )
        db.session.add(history)
        db.session.commit()
        
        flash('Пользователь успешно зарегистрирован!', 'success')
        return redirect(url_for('main.users'))
    
    return render_template('auth/register.html', title='Регистрация', form=form)