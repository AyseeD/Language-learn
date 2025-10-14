from flask import Flask, request, jsonify
import tensorflow as tf
from PIL import Image, ImageOps
import numpy as np
import io
import base64

# ==========================
# LOAD MODEL + LABEL MAP
# ==========================
model = tf.keras.models.load_model("kanji_cnn_model.keras")

label_map = []
with open("kanji_labels.txt", "r", encoding="utf-8") as f:
    for line in f:
        parts = line.strip().split("\t")
        if len(parts) >= 3:
            label_map.append((parts[1], parts[2]))  # (class_id, kanji_char)

app = Flask(__name__)

# ==========================
# PREDICTION ENDPOINT (File Upload)
# ==========================
@app.route("/predict", methods=["POST"])
def predict():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    try:
        # 1️⃣ Read the file directly into PIL
        img_stream = file.stream
        img_stream.seek(0)  # Reset stream position
        img = Image.open(img_stream)
        
        print(f"📷 Received image: mode={img.mode}, size={img.size}, format={img.format}")

        # 2️⃣ Process the image
        processed_img = preprocess_image(img)
        
        # 3️⃣ Convert to model input format
        img_array = np.array(processed_img) / 255.0
        print(f"🔄 After processing - Range: {img_array.min():.3f} to {img_array.max():.3f}, Mean: {img_array.mean():.3f}")
        
        # 4️⃣ Convert to 3-channel and add batch dimension
        img_array = np.stack([img_array] * 3, axis=-1)  # (64, 64, 3)
        img_array = np.expand_dims(img_array, axis=0)   # (1, 64, 64, 3)
        
        # 5️⃣ Make prediction
        preds = model.predict(img_array, verbose=0)
        idx = np.argmax(preds[0])
        confidence = float(preds[0][idx])
        
        # 6️⃣ Get top predictions
        top_5_indices = np.argsort(preds[0])[-5:][::-1]
        top_predictions = [
            {"kanji": label_map[i][1], "confidence": float(preds[0][i])} 
            for i in top_5_indices
        ]
        
        class_id, kanji_char = label_map[idx]

        return jsonify({
            "predicted_class": class_id,
            "kanji": kanji_char,
            "confidence": confidence,
            "debug_info": {
                "image_range": f"{img_array.min():.3f} to {img_array.max():.3f}",
                "image_mean": f"{img_array.mean():.3f}",
                "top_5_predictions": top_predictions
            }
        })

    except Exception as e:
        print("❌ Error processing image:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ==========================
# BASE64 PREDICTION ENDPOINT
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

        # Process the image
        processed_img = preprocess_image(img)
        
        # Convert to model input
        img_array = np.array(processed_img) / 255.0
        print(f"🔄 After processing - Range: {img_array.min():.3f} to {img_array.max():.3f}, Mean: {img_array.mean():.3f}")
        
        img_array = np.stack([img_array] * 3, axis=-1)
        img_array = np.expand_dims(img_array, axis=0)
        
        # Make prediction
        preds = model.predict(img_array, verbose=0)
        idx = np.argmax(preds[0])
        confidence = float(preds[0][idx])
        
        class_id, kanji_char = label_map[idx]

        return jsonify({
            "predicted_class": class_id,
            "kanji": kanji_char,
            "confidence": confidence
        })

    except Exception as e:
        print("❌ Error processing base64 image:", e)
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ==========================
# IMAGE PREPROCESSING FUNCTION
# ==========================
def preprocess_image(img):
    """Convert any image to the format expected by the model"""
    
    # 1️⃣ Convert to RGB if needed
    if img.mode != 'RGB':
        img = img.convert('RGB')
    
    # 2️⃣ Convert to grayscale
    img = img.convert('L')
    
    # 3️⃣ DEBUG: Save original for inspection
    img.save("debug_original.png")
    original_array = np.array(img)
    print(f"📊 Original grayscale - Range: {original_array.min()} to {original_array.max()}, Mean: {original_array.mean():.3f}")
    
    # 4️⃣ Check if we need to invert - Kuzushiji typically has white strokes on black background
    white_pixels = np.sum(original_array > 200)  # Bright pixels
    black_pixels = np.sum(original_array < 50)   # Dark pixels
    mid_pixels = np.sum((original_array >= 50) & (original_array <= 200))
    
    print(f"⚪ Bright pixels (>200): {white_pixels}")
    print(f"⚫ Dark pixels (<50): {black_pixels}")
    print(f"🎨 Mid pixels: {mid_pixels}")
    
    # If we have mostly dark background, keep as is (Kuzushiji format)
    # If we have mostly light background, invert
    if black_pixels < white_pixels:
        img = ImageOps.invert(img)
        print("🔄 Inverted image (white background -> black background)")
    
    # 5️⃣ Resize to model input size
    img = img.resize((64, 64), Image.LANCZOS)
    
    # 6️⃣ DEBUG: Save processed image
    img.save("debug_processed.png")
    processed_array = np.array(img)
    print(f"📊 Processed image - Range: {processed_array.min()} to {processed_array.max()}, Mean: {processed_array.mean():.3f}")
    
    return img

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
        "endpoints": [
            "/predict (POST) - file upload",
            "/predict-base64 (POST) - base64 data", 
            "/test (GET) - health check"
        ]
    })

# ==========================
# MAIN
# ==========================
if __name__ == "__main__":
    print("✅ Kanji Prediction API running on http://127.0.0.1:5001")
    print(f"✅ Loaded {len(label_map)} classes")
    print("✅ Endpoints:")
    print("   - POST /predict (file upload)")
    print("   - POST /predict-base64 (base64 data)")
    print("   - GET  /test (health check)")
    app.run(port=5001, debug=True)