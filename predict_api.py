from flask import Flask, request, jsonify
import tensorflow as tf
from PIL import Image, ImageOps, ImageFilter
import numpy as np
import io
import base64
import cv2
import os

# ==========================
# LOAD MODEL + LABEL MAP
# ==========================
# Try to load the best model first, fallback to regular model
model_path = "best_kanji_model.keras" if os.path.exists("best_kanji_model.keras") else "kanji_cnn_model.keras"
print(f"🔄 Loading model from: {model_path}")
model = tf.keras.models.load_model(model_path)

label_map = []
with open("kanji_labels.txt", "r", encoding="utf-8") as f:
    for line in f:
        parts = line.strip().split("\t")
        if len(parts) >= 3:
            label_map.append((parts[1], parts[2]))  # (class_id, kanji_char)

app = Flask(__name__)

# ==========================
# ENHANCED PREDICTION ENDPOINT
# ==========================
@app.route("/predict", methods=["POST"])
def predict():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    try:
        # Read the file directly into PIL
        img_stream = file.stream
        img_stream.seek(0)
        img = Image.open(img_stream)
        
        print(f"📷 Received image: mode={img.mode}, size={img.size}")

        # Process the image with enhanced preprocessing
        processed_img = enhanced_preprocess_image(img)
        
        # Convert to model input format
        img_array = np.array(processed_img) / 255.0
        print(f"🔄 After processing - Range: {img_array.min():.3f} to {img_array.max():.3f}, Mean: {img_array.mean():.3f}")
        
        # Convert to 3-channel and add batch dimension
        img_array = np.stack([img_array] * 3, axis=-1)
        img_array = np.expand_dims(img_array, axis=0)
        
        # Make prediction with enhanced logic
        return enhanced_prediction_logic(img_array)

    except Exception as e:
        print("❌ Error processing image:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ==========================
# ENHANCED BASE64 PREDICTION ENDPOINT
# ==========================
@app.route("/predict-base64", methods=["POST"])
def predict_base64():
    try:
        data = request.get_json()
        if not data or "image" not in data:
            return jsonify({"error": "No image data"}), 400

        # Extract base64 data
        img_data = data["image"]
        if img_data.startswith("data:image/png;base64,"):
            img_data = img_data.replace("data:image/png;base64,", "")

        # Decode base64
        img_bytes = base64.b64decode(img_data)
        img = Image.open(io.BytesIO(img_bytes))
        
        print(f"📷 Base64 image: mode={img.mode}, size={img.size}")

        # Process the image with enhanced preprocessing
        processed_img = enhanced_preprocess_image(img)
        
        # Convert to model input
        img_array = np.array(processed_img) / 255.0
        print(f"🔄 After processing - Range: {img_array.min():.3f} to {img_array.max():.3f}, Mean: {img_array.mean():.3f}")
        
        img_array = np.stack([img_array] * 3, axis=-1)
        img_array = np.expand_dims(img_array, axis=0)
        
        # Make prediction with enhanced logic
        return enhanced_prediction_logic(img_array)

    except Exception as e:
        print("❌ Error processing base64 image:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ==========================
# ENHANCED IMAGE PREPROCESSING
# ==========================
def enhanced_preprocess_image(img):
    """Enhanced preprocessing to match training data better"""
    
    # 1️⃣ Convert to grayscale
    if img.mode != 'L':
        img = img.convert('L')
    
    # Save original for debug
    img.save("debug_original.png")
    original_array = np.array(img)
    print(f"📊 Original - Range: {original_array.min()} to {original_array.max()}")
    
    # 2️⃣ Apply binary thresholding for cleaner strokes
    img_array = np.array(img)
    
    # Use Otsu's thresholding if OpenCV is available, else use fixed threshold
    try:
        _, binary_array = cv2.threshold(img_array, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        img = Image.fromarray(binary_array)
        print("✅ Used Otsu thresholding")
    except:
        # Fallback: manual threshold
        threshold = 128
        img = img.point(lambda p: 255 if p > threshold else 0)
        print("✅ Used manual thresholding")
    
    # 3️⃣ Analyze and invert if needed
    img_array = np.array(img)
    white_pixels = np.sum(img_array == 255)
    black_pixels = np.sum(img_array == 0)
    
    print(f"⚪ White pixels: {white_pixels}, ⚫ Black pixels: {black_pixels}")
    
    # Kuzushiji dataset has white strokes on black background
    # If user drew black on white, we need to invert
    if white_pixels > black_pixels:
        img = ImageOps.invert(img)
        print("🔄 Inverted to match Kuzushiji format")
    
    # 4️⃣ Remove small noise
    img = img.filter(ImageFilter.MedianFilter(3))
    
    # 5️⃣ Resize with high quality
    img = img.resize((64, 64), Image.LANCZOS)
    
    # 6️⃣ Add slight stroke thickening to match training data
    img = img.filter(ImageFilter.MaxFilter(3))
    
    img.save("debug_processed.png")
    processed_array = np.array(img)
    print(f"📊 Processed - Range: {processed_array.min()} to {processed_array.max()}, Mean: {processed_array.mean():.3f}")
    
    return img

# ==========================
# ENHANCED PREDICTION LOGIC
# ==========================
def enhanced_prediction_logic(img_array):
    """Enhanced prediction with confidence thresholds and suggestions"""
    
    # Make prediction
    preds = model.predict(img_array, verbose=0)
    
    # Get top predictions
    top_5_indices = np.argsort(preds[0])[-5:][::-1]
    top_confidence = float(preds[0][top_5_indices[0]])
    second_confidence = float(preds[0][top_5_indices[1]])
    
    # Calculate confidence gap
    confidence_gap = top_confidence - second_confidence
    
    # Enhanced decision logic
    confidence_threshold_high = 0.7
    confidence_threshold_low = 0.3
    confidence_gap_threshold = 0.2
    
    idx = top_5_indices[0]
    class_id, kanji_char = label_map[idx]
    
    # Prepare suggestions
    suggestions = [
        {"kanji": label_map[i][1], "confidence": float(preds[0][i])} 
        for i in top_5_indices
    ]
    
    # Determine result type and message
    if top_confidence > confidence_threshold_high and confidence_gap > confidence_gap_threshold:
        result_type = "high_confidence"
        message = "High confidence prediction"
    elif top_confidence > confidence_threshold_low:
        result_type = "medium_confidence"
        message = f"Moderate confidence. Top 2: {suggestions[0]['kanji']} ({suggestions[0]['confidence']*100:.1f}%) vs {suggestions[1]['kanji']} ({suggestions[1]['confidence']*100:.1f}%)"
    else:
        result_type = "low_confidence"
        message = "Low confidence. Try drawing more clearly with thicker strokes."
        kanji_char = "?"  # Show question mark for very low confidence
    
    return jsonify({
        "predicted_class": class_id,
        "kanji": kanji_char,
        "confidence": top_confidence,
        "result_type": result_type,
        "message": message,
        "suggestions": suggestions,
        "confidence_gap": confidence_gap,
        "debug_info": {
            "image_range": f"{img_array.min():.3f} to {img_array.max():.3f}",
            "image_mean": f"{img_array.mean():.3f}",
        }
    })

# ==========================
# MODEL INFO ENDPOINT
# ==========================
@app.route("/model-info", methods=["GET"])
def model_info():
    """Get information about the loaded model"""
    model_name = "best_kanji_model.keras" if os.path.exists("best_kanji_model.keras") else "kanji_cnn_model.keras"
    return jsonify({
        "model_loaded": model_name,
        "classes_loaded": len(label_map),
        "model_exists": os.path.exists(model_name),
        "best_model_exists": os.path.exists("best_kanji_model.keras")
    })

# ==========================
# TEST ENDPOINT
# ==========================
@app.route("/test", methods=["GET"])
def test_endpoint():
    """Test if the API is working"""
    return jsonify({
        "status": "API is running",
        "model_loaded": True,
        "classes_loaded": len(label_map),
        "model_source": "best_kanji_model.keras" if os.path.exists("best_kanji_model.keras") else "kanji_cnn_model.keras",
        "endpoints": [
            "/predict (POST) - file upload",
            "/predict-base64 (POST) - base64 data", 
            "/test (GET) - health check",
            "/model-info (GET) - model information"
        ]
    })

# ==========================
# MAIN
# ==========================
if __name__ == "__main__":
    model_source = "best_kanji_model.keras" if os.path.exists("best_kanji_model.keras") else "kanji_cnn_model.keras"
    print("✅ Enhanced Kanji Prediction API running on http://127.0.0.1:5001")
    print(f"✅ Loaded {len(label_map)} classes")
    print(f"✅ Model source: {model_source}")
    print("✅ Features: Enhanced preprocessing, confidence thresholds, suggestions")
    app.run(port=5001, debug=True)