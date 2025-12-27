import random
from datetime import datetime
from io import BytesIO

from flask import render_template, Blueprint, session, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from gtts import gTTS

from app.database.models import Character, Course, Progress, Enrollment
from app import get_session

course = Blueprint('course', __name__)

@course.route('/<course_name>/draw', methods=['GET'])
@login_required
def draw(course_name):
    if hasattr(current_user, 'id'):
        print(f"User ID: {current_user.id}")
    else:
        print("User has no ID attribute!")
        flash('Authentication error. Please log in again.', 'error')
        return redirect(url_for('auth.login'))

    with get_session() as db:
        # Check if user is enrolled in this course
        course_obj = db.query(Course).filter_by(name=course_name).first()

        if not course_obj:
            flash('Course not found', 'error')
            return redirect(url_for('customer.courses'))

        course_id = course_obj.id

        enrollment = db.query(Enrollment).filter_by(
            user_id=current_user.id,
            course_id=course_id
        ).first()

        if not enrollment:
            return "Not enrolled in this course", 403

        # Get course details
        course = db.query(Course).filter_by(id=course_id).first()
        if not course:
            return "Course not found", 404

        # Get all characters for this course
        all_characters = db.query(Character).filter_by(course_id=course_id).all()

        if not all_characters:
            return "No characters available for this course", 404

        # Get user's progress
        learned_progress = db.query(Progress).filter_by(
            user_id=current_user.id,
            course_id=course_id,
            learned=True
        ).all()

        learned_character_ids = {p.character_id for p in learned_progress}

        # Filter unlearned characters
        unlearned_characters = [
            char for char in all_characters
            if char.id not in learned_character_ids
        ]

        # If all learned, pick from all characters
        available_characters = unlearned_characters if unlearned_characters else all_characters

        # Select random character
        selected_character = random.choice(available_characters)

        # Store in session for verification
        session['current_character_id'] = selected_character.id
        session['current_course_id'] = course_id

        # Calculate progress percentage
        progress_percentage = (len(learned_character_ids) / len(all_characters)) * 100 if all_characters else 0

        if course_name.lower() == 'hiragana':
            return render_template('customer/draw.html',  # Use the draw.html in templates root
                                   character=selected_character,
                                   course=course,
                                   progress=progress_percentage)
        else:
            return render_template(
                'customer/draw.html',  # Use customer/draw.html for other courses
                character=selected_character,
                course=course,
                progress=progress_percentage
            )


# The rest of your existing code remains the same...
@course.route('/<course_name>/learn', methods=['GET'])
@login_required
def learn(course_name):
    with get_session() as db:
        # Get course details
        course_obj = db.query(Course).filter_by(name=course_name).first()
        if not course_obj:
            flash("Course not found", "error")
            return redirect(url_for('customer.courses'))  # Changed from main.index

        # Check if user is enrolled in this course
        enrollment = db.query(Enrollment).filter_by(
            user_id=current_user.id,
            course_id=course_obj.id
        ).first()

        if not enrollment:
            flash("You are not enrolled in this course", "error")
            return redirect(url_for('customer.courses'))  # Changed from main.index

        # Get all characters for this course
        all_characters = db.query(Character).filter_by(course_id=course_obj.id).all()

        if not all_characters:
            flash("No characters available for this course", "error")
            return redirect(url_for('customer.courses'))  # Changed from main.index

        # Get user's progress
        learned_progress = db.query(Progress).filter_by(
            user_id=current_user.id,
            course_id=course_obj.id,
            learned=True
        ).all()

        learned_character_ids = {p.character_id for p in learned_progress}

        # Filter unlearned characters
        unlearned_characters = [
            char for char in all_characters
            if char.id not in learned_character_ids
        ]

        # If all learned, pick from all characters
        available_characters = unlearned_characters if unlearned_characters else all_characters

        # Select random character
        selected_character = random.choice(available_characters)

        # Store in session for tracking
        session['current_character_id'] = selected_character.id
        session['current_course_id'] = course_obj.id

        # Calculate progress percentage
        progress_percentage = (len(learned_character_ids) / len(all_characters)) * 100 if all_characters else 0

        return render_template(
            'customer/learn.html',
            character=selected_character,
            course=course_obj,
            progress=progress_percentage
        )


@course.route('/<course_name>/tts/<int:character_id>', methods=['GET'])
def tts(course_name, character_id):
    with get_session() as db:
        # Get the character
        character = db.query(Character).filter_by(id=character_id).first()

        if not character:
            return "Character not found", 404

        # Generate TTS audio using gTTS
        try:
            tts = gTTS(text=character.kana, lang='ja', slow=False)

            # Save to BytesIO object
            audio_io = BytesIO()
            tts.write_to_fp(audio_io)
            audio_io.seek(0)

            return send_file(
                audio_io,
                mimetype='audio/mpeg',
                as_attachment=False,
                download_name=f'{character.romaji}.mp3'
            )
        except Exception as e:
            return f"Error generating audio: {str(e)}", 500


@course.route('/<course_name>/learn/next', methods=['POST'])
@login_required
def learn_next(course_name):
    with get_session() as db:
        # Get current character from session
        current_character_id = session.get('current_character_id')
        current_course_id = session.get('current_course_id')

        if not current_character_id or not current_course_id:
            flash("Session expired. Please start again.", "error")
            return redirect(url_for('course.learn', course_name=course_name))

        # Mark current character as learned
        progress = db.query(Progress).filter_by(
            user_id=current_user.id,
            course_id=current_course_id,
            character_id=current_character_id
        ).first()

        if progress:
            # Update existing progress
            progress.learned = True
            progress.answered = True
            progress.updated_at = datetime.utcnow()
        else:
            # Create new progress record
            new_progress = Progress(
                user_id=current_user.id,
                course_id=current_course_id,
                character_id=current_character_id,
                learned=True,
                answered=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(new_progress)

        db.commit()

        # Redirect to learn page to show next character
        return redirect(url_for('course.learn', course_name=course_name))


@course.route('/<course_name>/learn/previous', methods=['POST'])
@login_required
def learn_previous(course_name):
    with get_session() as db:
        # Get course details
        course_obj = db.query(Course).filter_by(name=course_name).first()
        if not course_obj:
            flash("Course not found", "error")
            return redirect(url_for('customer.courses'))  # Changed from main.index

        # Get all characters for this course
        all_characters = db.query(Character).filter_by(course_id=course_obj.id).all()

        if not all_characters:
            flash("No characters available", "error")
            return redirect(url_for('customer.courses'))  # Changed from main.index

        # Get current character from session
        current_character_id = session.get('current_character_id')

        # Find current character index
        current_index = next((i for i, char in enumerate(all_characters) if char.id == current_character_id), 0)

        # Get previous character (wrap around if at beginning)
        previous_index = (current_index - 1) % len(all_characters)
        selected_character = all_characters[previous_index]

        # Update session
        session['current_character_id'] = selected_character.id
        session['current_course_id'] = course_obj.id

        # Get user's progress for percentage calculation
        learned_progress = db.query(Progress).filter_by(
            user_id=current_user.id,
            course_id=course_obj.id,
            learned=True
        ).all()

        learned_character_ids = {p.character_id for p in learned_progress}
        progress_percentage = (len(learned_character_ids) / len(all_characters)) * 100 if all_characters else 0

        return render_template(
            'customer/learn.html',
            character=selected_character,
            course=course_obj,
            progress=progress_percentage
        )