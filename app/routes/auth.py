import sqlalchemy as sa
from flask import Blueprint, render_template, redirect, flash, url_for
from flask_login import current_user, login_user, login_required, logout_user

from app import get_session
from app.database.models import User
from app.web.forms.auth import LoginForm, RegistrationForm

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        with get_session() as session:
            user = session.scalar(
                sa.select(User).where(User.username == form.username.data))
            if user is None or not user.verify_password(form.password.data):
                flash('Invalid username or password')
                return redirect(url_for('auth.login'))
            login_user(user, remember=form.remember_me.data)
            return redirect(url_for('customer.courses'))
    return render_template('auth/login.html', title='Log In', form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'success')
    return redirect(url_for('index'))


@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(name=form.name.data,
                    username=form.username.data,
                    password=form.password.data)
        with get_session() as session:
            session.add(user)
            session.commit()
            flash('You can now login.')
            return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title="Sign In", form=form)
