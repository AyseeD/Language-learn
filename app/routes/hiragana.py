import sys
import os
from flask import Blueprint, request, jsonify, session
from flask_login import login_required, current_user
from datetime import datetime

# Get the absolute path to the project root
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))  # Goes up two levels from app/routes

# Add model directory to path - THREE possible locations to try
possible_model_paths = [
    os.path.join(project_root, 'app', 'model'),  # /Language-learn/app/model
    os.path.join(project_root, 'model'),         # /Language-learn/model
    os.path.join(current_dir, '..', 'model'),    # /app/routes/../model
]

model_path_added = False
for model_path in possible_model_paths:
    if os.path.exists(model_path):
        sys.path.insert(0, model_path)  # Insert at beginning to ensure it's found first
        sys.path.insert(0, os.path.dirname(model_path))  # Also add parent directory
        print(f"✅ Added model path: {model_path}")
        model_path_added = True
        break

if not model_path_added:
    print(f"❌ Could not find model directory. Tried:")
    for path in possible_model_paths:
        print(f"  - {path}")
    
    # Print current directory structure for debugging
    print(f"\nCurrent directory: {current_dir}")
    print(f"Project root: {project_root}")
    print(f"Files in project root:")
    try:
        for item in os.listdir(project_root):
            print(f"  - {item}")
    except:
        pass

# Import the recognizer
try:
    from predict_character import get_recognizer
    recognizer = get_recognizer()
    print("✅ Hiragana recognizer loaded successfully in hiragana blueprint")
    print(f"📚 Characters available: {list(recognizer.label_encoder['index_to_char'].values())}")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"Current sys.path:")
    for path in sys.path:
        print(f"  - {path}")
    recognizer = None
except Exception as e:
    print(f"❌ Failed to load recognizer in hiragana blueprint: {e}")
    import traceback
    traceback.print_exc()
    recognizer = None

hiragana_bp = Blueprint('hiragana', __name__, url_prefix='/hiragana')

# Rest of the code remains the same...
@hiragana_bp.route('/predict', methods=['POST'])
@login_required
def predict_character():
    """
    Handle character prediction from drawing
    """
    if recognizer is None:
        return jsonify({
            'success': False,
            'error': 'Recognizer not initialized. Please try again later.'
        }), 500
    
    try:
        data = request.get_json()
        
        if not data or 'image' not in data:
            return jsonify({
                'success': False,
                'error': 'No image data provided'
            }), 400
        
        # Get the target character from session (if available)
        current_character_id = session.get('current_character_id')
        current_course_id = session.get('current_course_id')
        
        target_char = None
        if current_character_id and current_course_id:
            from app import get_session
            from app.database.models import Character
            
            with get_session() as db:
                character = db.query(Character).filter_by(id=current_character_id).first()
                if character:
                    target_char = character.kana
        
        # Get image data
        image_data = data['image']
        
        # Make prediction
        result = recognizer.predict(image_data, target_char)
        
        # If prediction is correct, update progress
        if result.get('is_correct', False) and current_character_id and current_course_id:
            from app.database.models import Progress
            
            with get_session() as db:
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
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@hiragana_bp.route('/skip', methods=['POST'])
@login_required
def skip_character():
    """
    Skip current character
    """
    try:
        current_character_id = session.get('current_character_id')
        current_course_id = session.get('current_course_id')
        
        if not current_character_id or not current_course_id:
            return jsonify({
                'success': False,
                'error': 'No active character to skip'
            }), 400
        
        from app import get_session
        from app.database.models import Progress
        
        with get_session() as db:
            # Mark as skipped (not learned)
            progress = db.query(Progress).filter_by(
                user_id=current_user.id,
                course_id=current_course_id,
                character_id=current_character_id
            ).first()

            if progress:
                # Update existing progress
                progress.learned = False
                progress.answered = False
                progress.updated_at = datetime.utcnow()
            else:
                # Create new progress record (marked as not learned)
                new_progress = Progress(
                    user_id=current_user.id,
                    course_id=current_course_id,
                    character_id=current_character_id,
                    learned=False,
                    answered=False,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(new_progress)
            db.commit()
        
        return jsonify({
            'success': True,
            'message': 'Character skipped',
            'redirect': '/dashboard/courses'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500