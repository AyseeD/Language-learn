from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy.orm import Session
from app.database.models import Course, Enrollment, Transaction, Pricing
from app import get_engine

customer = Blueprint('customer', __name__)


@login_required
@customer.route('/courses', methods=['GET'])
def courses():
    engine = get_engine()
    with Session(engine) as db:
        # Get all courses
        all_courses = db.query(Course).all()

        # Get user's enrollments
        enrolled_course_ids = db.query(Enrollment.course_id).filter(
            Enrollment.user_id == current_user.id
        ).all()
        enrolled_course_ids = [e[0] for e in enrolled_course_ids]

        # Get pricing for all courses
        course_prices = {}
        for course in all_courses:
            pricing = db.query(Pricing).filter(Pricing.course_id == course.id).first()
            if pricing:
                course_prices[course.name] = pricing.price

        return render_template('customer/courses.html',
                               enrolled_courses=enrolled_course_ids,
                               course_prices=course_prices)


@customer.route('/purchase', methods=['POST'])
@login_required
def purchase():
    engine = get_engine()

    try:
        data = request.get_json()
        course_name = data.get('course_name')
        card_number = data.get('card_number')

        if not course_name or not card_number:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        # Validate card number (basic validation)
        if len(card_number) < 13 or len(card_number) > 19:
            return jsonify({'success': False, 'message': 'Invalid card number'}), 400

        with Session(engine) as db:
            # Get course
            course = db.query(Course).filter(Course.name == course_name).first()
            if not course:
                return jsonify({'success': False, 'message': 'Course not found'}), 404

            # Check if already enrolled
            existing_enrollment = db.query(Enrollment).filter(
                Enrollment.user_id == current_user.id,
                Enrollment.course_id == course.id
            ).first()

            if existing_enrollment:
                return jsonify({'success': False, 'message': 'Already enrolled in this course'}), 400

            # Get pricing
            pricing = db.query(Pricing).filter(Pricing.course_id == course.id).first()
            if not pricing:
                return jsonify({'success': False, 'message': 'Pricing not found'}), 404

            # Create transaction
            transaction = Transaction(
                user_id=current_user.id,
                course_id=course.id,
                card_number=card_number,
                price=pricing.price
            )
            db.add(transaction)
            db.flush()  # Get transaction ID

            # Create enrollment
            enrollment = Enrollment(
                user_id=current_user.id,
                course_id=course.id,
                transaction_id=transaction.id
            )
            db.add(enrollment)

            db.commit()

            return jsonify({
                'success': True,
                'message': f'Successfully enrolled in {course_name}!'
            }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500