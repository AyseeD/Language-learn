from flask import Flask, request, jsonify
import tensorflow as tf
from PIL import Image, ImageOps, ImageFilter
import numpy as np
import io

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
# PREDICTION ENDPOINT
# ==========================
@app.route("/predict", methods=["POST"])
def predict():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    try:
        # 1️⃣ Load + grayscale + invert
        img = Image.open(file).convert("L")
        img = ImageOps.invert(img)

        # 2️⃣ Binarize (pure black & white)
        img = img.point(lambda x: 0 if x < 128 else 255, '1')

        # 3️⃣ Find bounding box of drawing
        bbox = img.getbbox()
        if bbox:
            img = img.crop(bbox)

        # 4️⃣ Resize with padding to square (64x64) maintaining aspect ratio
        img.thumbnail((56, 56), Image.LANCZOS)
        new_img = Image.new("L", (64, 64), 0)  # black background
        paste_x = (64 - img.width) // 2
        paste_y = (64 - img.height) // 2
        new_img.paste(img, (paste_x, paste_y))

        # 5️⃣ Optional: slightly thicken strokes to match dataset
        new_img = new_img.filter(ImageFilter.MaxFilter(3))

        # 6️⃣ Normalize and expand dimensions
        img = np.array(new_img) / 255.0
        img = np.stack((img,) * 3, axis=-1)
        img = np.expand_dims(img, axis=0)

        preds = model.predict(img)
        idx = np.argmax(preds[0])
        class_id, kanji_char = label_map[idx]
        confidence = float(preds[0][idx])

        return jsonify({
            "predicted_class": class_id,
            "kanji": kanji_char,
            "confidence": confidence
        })

    except Exception as e:
        print("Error processing image:", e)
        return jsonify({"error": "Failed to process image"}), 500

# ==========================
# MAIN
# ==========================
if __name__ == "__main__":
    print("✅ Kanji Prediction API running on http://127.0.0.1:5001")
    app.run(port=5001)
