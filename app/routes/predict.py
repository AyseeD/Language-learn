import io
import base64
from pathlib import Path

import numpy as np
from flask import render_template, request, jsonify, Blueprint
from PIL import Image, ImageOps, ImageEnhance
from flask_login import login_required
from tensorflow import keras

prediction = Blueprint('prediction', __name__)

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / 'detection' / 'kanji_model.keras'
LABELS_FILE = BASE_DIR / 'detection' / 'kanji_labels.txt'
MODEL_INPUT_SIZE = (64, 64)

model = None
label_map = []


def load_kanji_labels():
    """Load Kanji characters from the labels file."""
    global label_map
    try:
        with open(LABELS_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) >= 3:
                    label_map.append((parts[1], parts[2]))
                else:
                    label_map.append(("", line.strip()))
        print(f"✅ Loaded {len(label_map)} kanji labels")
    except FileNotFoundError:
        print(f"❌ Label file not found: {LABELS_FILE}")
        print(f"   Looking in: {LABELS_FILE.absolute()}")
    except Exception as e:
        print(f"❌ Error loading labels: {e}")


def load_model():
    """Load the pre-trained Keras model."""
    global model
    try:
        model = keras.models.load_model(MODEL_PATH)
        print(f"✅ Model loaded from {MODEL_PATH}")
        print(f"   Input shape: {model.input_shape}")
        print(f"   Output shape: {model.output_shape}")
    except FileNotFoundError:
        print(f"❌ Model file not found: {MODEL_PATH}")
        print(f"   Looking in: {MODEL_PATH.absolute()}")
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        import traceback
        traceback.print_exc()


# Initialize on module load
load_kanji_labels()
load_model()


@login_required
@prediction.route('/kanji/draw', methods=['GET'])
def index():
    """Render the drawing canvas page."""
    return render_template('customer/draw.html')


def preprocess_image(img):
    """
    Convert image to format expected by the model.
    Handles various input formats and applies proper preprocessing.
    """

    # Convert to RGB if needed
    if img.mode == 'RGBA':
        # Create white background for transparent images
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # Convert to grayscale
    img = img.convert('L')

    # Get image statistics
    img_array = np.array(img)
    print(f"📊 Input image - Range: [{img_array.min()}, {img_array.max()}], Mean: {img_array.mean():.1f}")

    # Determine if we need to invert
    # Count bright vs dark pixels
    bright_pixels = np.sum(img_array > 200)
    dark_pixels = np.sum(img_array < 50)
    total_pixels = img_array.size

    bright_ratio = bright_pixels / total_pixels
    dark_ratio = dark_pixels / total_pixels

    print(f"   Bright pixels: {bright_ratio:.1%}, Dark pixels: {dark_ratio:.1%}")

    # If mostly bright background (like white canvas), invert to dark background
    if bright_ratio > 0.5:
        img = ImageOps.invert(img)
        print("   🔄 Inverted (white bg → black bg)")

    # Enhance contrast to make strokes more visible
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)

    # Resize to model input size
    img = img.resize(MODEL_INPUT_SIZE, Image.LANCZOS)

    # Final statistics
    final_array = np.array(img)
    print(f"📊 Processed - Range: [{final_array.min()}, {final_array.max()}], Mean: {final_array.mean():.1f}")

    return img


@login_required
@prediction.route('/kanji/predict', methods=['POST'])
def predict():
    """Handle image submission and return prediction."""

    # Validate model and labels are loaded
    if model is None:
        return jsonify({
            "success": False,
            "error": "Model not loaded. Check server logs."
        }), 500

    if not label_map:
        return jsonify({
            "success": False,
            "error": "Label map not loaded. Check server logs."
        }), 500

    # Get request data
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({
            "success": False,
            "error": "No image data provided"
        }), 400

    try:
        # Decode base64 image
        img_data = data['image']
        if img_data.startswith("data:image"):
            img_data = img_data.split(",", 1)[1]

        image_bytes = base64.b64decode(img_data)
        img = Image.open(io.BytesIO(image_bytes))

        print(f"\n📷 Received image: {img.mode} {img.size}")

        # Preprocess the image
        processed_img = preprocess_image(img)

        # Convert to numpy array and normalize
        img_array = np.array(processed_img).astype('float32') / 255.0

        # Convert to 3-channel RGB (model expects RGB)
        img_array = np.stack([img_array] * 3, axis=-1)  # (64, 64, 3)

        # Add batch dimension
        img_array = np.expand_dims(img_array, axis=0)  # (1, 64, 64, 3)

        print(f"🔢 Model input - Shape: {img_array.shape}, Range: [{img_array.min():.3f}, {img_array.max():.3f}]")

        # Make prediction
        predictions = model.predict(img_array, verbose=0)
        predicted_index = int(np.argmax(predictions[0]))  # Convert to Python int
        confidence = float(predictions[0][predicted_index])

        print(f"🎯 Predicted index: {predicted_index}, Confidence: {confidence:.3f}")

        # Get top 5 predictions
        top_5_indices = np.argsort(predictions[0])[-5:][::-1]
        top_predictions = []

        for idx in top_5_indices:
            idx = int(idx)  # Convert numpy int64 to Python int
            if idx < len(label_map):
                class_id, kanji = label_map[idx]
                top_predictions.append({
                    "kanji": kanji,
                    "confidence": float(predictions[0][idx]),
                    "class_id": class_id
                })

        # Get predicted kanji
        if 0 <= predicted_index < len(label_map):
            class_id, predicted_kanji = label_map[predicted_index]
        else:
            predicted_kanji = "?"
            class_id = "unknown"
            print(f"⚠️ Warning: Predicted index {predicted_index} out of range (0-{len(label_map) - 1})")

        print(f"✅ Result: {predicted_kanji} ({confidence * 100:.1f}%)\n")

        # Return response
        return jsonify({
            "success": True,
            "prediction": {
                "kanji": predicted_kanji,
                "confidence": confidence,
                "predicted_class": class_id,
                "debug_info": {
                    "image_range": f"{img_array.min():.3f} to {img_array.max():.3f}",
                    "image_mean": f"{img_array.mean():.3f}",
                    "top_5_predictions": top_predictions,
                    "predicted_index": predicted_index,
                    "total_classes": len(label_map)
                }
            }
        })

    except Exception as e:
        print(f"❌ Prediction error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Prediction failed: {str(e)}"
        }), 500