from flask import render_template, Blueprint, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime
from sqlalchemy import func

from app.database.models import User, Course, Character, Pricing, Transaction, Enrollment, Progress, Role
from app import get_session

admin = Blueprint('admin', __name__)


# Create a custom decorator for admin pages to allow only admin users
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role_code != 'ADMIN':
            flash('You need administrator privileges to access this page.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)

    return decorated_function


@admin.route('/')
@login_required
@admin_required
def dashboard():
    with get_session() as db:
        # Get statistics
        total_users = db.query(User).count()
        total_courses = db.query(Course).count()
        total_enrollments = db.query(Enrollment).count()
        total_revenue = db.query(func.sum(Transaction.price)).scalar()

        # Recent transactions
        recent_transactions = db.query(Transaction).order_by(
            Transaction.created_at.desc()
        ).limit(5).all()

        return render_template(
            'admin/dashboard.html',
            total_users=total_users,
            total_courses=total_courses,
            total_enrollments=total_enrollments,
            total_revenue=total_revenue,
            recent_transactions=recent_transactions
        )


@admin.route('/users')
@login_required
@admin_required
def users():
    with get_session() as db:
        all_users = db.query(User).all()
        return render_template('admin/users.html', users=all_users)


@admin.route('/users/<int:user_id>')
@login_required
@admin_required
def user_detail(user_id):
    with get_session() as db:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('admin.users'))

        # Get user's enrollments with course info
        enrollments = db.query(Enrollment).filter_by(user_id=user_id).all()

        # Enrich enrollments with course and transaction data
        enrollment_data = []
        for enrollment in enrollments:
            course = db.query(Course).filter_by(id=enrollment.course_id).first()
            transaction = db.query(Transaction).filter_by(id=enrollment.transaction_id).first()
            enrollment_data.append({
                'enrollment': enrollment,
                'course': course,
                'transaction': transaction
            })

        # Get user's progress grouped by course
        progress_data = {}
        for enrollment in enrollments:
            course = db.query(Course).filter_by(id=enrollment.course_id).first()
            total_chars = db.query(Character).filter_by(course_id=enrollment.course_id).count()
            learned_chars = db.query(Progress).filter_by(
                user_id=user_id,
                course_id=enrollment.course_id,
                learned=True
            ).count()

            if course:
                progress_data[course.name] = {
                    'total': total_chars,
                    'learned': learned_chars,
                    'percentage': (learned_chars / total_chars * 100) if total_chars > 0 else 0
                }

        # Get user's transactions
        transactions = db.query(Transaction).filter_by(user_id=user_id).all()

        return render_template(
            'admin/user_detail.html',
            user=user,
            enrollment_data=enrollment_data,
            progress_data=progress_data,
            transactions=transactions
        )


@admin.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    with get_session() as db:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('admin.users'))

        if request.method == 'POST':
            user.name = request.form.get('name')
            user.username = request.form.get('username')
            role_code = request.form.get('role_code')

            if role_code:
                user.role_code = role_code

            user.updated_at = datetime.utcnow()
            db.commit()

            flash('User updated successfully', 'success')
            return redirect(url_for('admin.user_detail', user_id=user_id))

        roles = db.query(Role).all()
        return render_template('admin/user_edit.html', user=user, roles=roles)


@admin.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    with get_session() as db:
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            flash('User not found', 'error')
            return redirect(url_for('admin.users'))

        if user.id == current_user.id:
            flash('You cannot delete your own account', 'error')
            return redirect(url_for('admin.users'))

        db.delete(user)
        db.commit()

        flash('User deleted successfully', 'success')
        return redirect(url_for('admin.users'))


@admin.route('/pricing')
@login_required
@admin_required
def pricing():
    with get_session() as db:
        courses = db.query(Course).all()
        pricing_data = []

        for course in courses:
            pricing = db.query(Pricing).filter_by(course_id=course.id).first()
            pricing_data.append({
                'course': course,
                'pricing': pricing
            })

        return render_template('admin/pricing.html', pricing_data=pricing_data)


@admin.route('/pricing/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_pricing(course_id):
    with get_session() as db:
        course = db.query(Course).filter_by(id=course_id).first()
        if not course:
            flash('Course not found', 'error')
            return redirect(url_for('admin.pricing'))

        pricing = db.query(Pricing).filter_by(course_id=course_id).first()

        if request.method == 'POST':
            new_price = request.form.get('price')

            if pricing:
                pricing.price = int(new_price)
            else:
                pricing = Pricing(course_id=course_id, price=int(new_price))
                db.add(pricing)

            db.commit()

            flash('Pricing updated successfully', 'success')
            return redirect(url_for('admin.pricing'))

        return render_template('admin/pricing_edit.html', course=course, pricing=pricing)


@admin.route('/transactions')
@login_required
@admin_required
def transactions():
    with get_session() as db:
        page = request.args.get('page', 1, type=int)
        per_page = 20

        all_transactions = db.query(Transaction).order_by(
            Transaction.created_at.desc()
        ).all()

        # Calculate total revenue
        total_revenue = sum(t.price for t in all_transactions)

        return render_template(
            'admin/transactions.html',
            transactions=all_transactions,
            total_revenue=total_revenue
        )


@admin.route('/transactions/<int:transaction_id>')
@login_required
@admin_required
def transaction_detail(transaction_id):
    with get_session() as db:
        transaction = db.query(Transaction).filter_by(id=transaction_id).first()
        if not transaction:
            flash('Transaction not found', 'error')
            return redirect(url_for('admin.transactions'))

        return render_template('admin/transaction_detail.html', transaction=transaction)

@admin.route('/enrollments')
@login_required
@admin_required
def enrollments():
    with get_session() as db:
        all_enrollments = db.query(Enrollment).all()

        # Group enrollments by course
        enrollment_by_course = {}
        for enrollment in all_enrollments:
            course = db.query(Course).filter_by(id=enrollment.course_id).first()
            if course.name not in enrollment_by_course:
                enrollment_by_course[course.name] = []
            enrollment_by_course[course.name].append(enrollment)

        return render_template(
            'admin/enrollments.html',
            enrollments=all_enrollments,
            enrollment_by_course=enrollment_by_course
        )

@admin.route('/progress')
@login_required
@admin_required
def progress():
    with get_session() as db:
        courses = db.query(Course).all()
        progress_stats = []

        for course in courses:
            total_chars = db.query(Character).filter_by(course_id=course.id).count()
            enrollments = db.query(Enrollment).filter_by(course_id=course.id).all()

            for enrollment in enrollments:
                user = db.query(User).filter_by(id=enrollment.user_id).first()
                learned = db.query(Progress).filter_by(
                    user_id=enrollment.user_id,
                    course_id=course.id,
                    learned=True
                ).count()

                progress_stats.append({
                    'user': user,
                    'course': course,
                    'learned': learned,
                    'total': total_chars,
                    'percentage': (learned / total_chars * 100) if total_chars > 0 else 0
                })

        return render_template('admin/progress.html', progress_stats=progress_stats)