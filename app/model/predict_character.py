import numpy as np
import cv2
import tensorflow as tf
from tensorflow import keras
import pickle
import json
import base64
from io import BytesIO
from PIL import Image
import os

class HiraganaRecognizer:
    def __init__(self, model_path=None):
        """
        Initialize the Hiragana recognizer
        """
        # Determine base directory
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Set default paths if not provided
        if model_path is None:
            model_path = os.path.join(self.base_dir, 'hiragana_model.keras')
        
        print(f"Loading model from: {model_path}")
        print(f"Base directory: {self.base_dir}")
        
        # Check if model file exists
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        # Load model
        self.model = keras.models.load_model(model_path)
        print("✅ Model loaded successfully")
        
        # Load label encoder
        label_encoder_path = os.path.join(self.base_dir, 'label_encoder.pkl')
        if not os.path.exists(label_encoder_path):
            raise FileNotFoundError(f"Label encoder not found: {label_encoder_path}")
        
        with open(label_encoder_path, 'rb') as f:
            self.label_encoder = pickle.load(f)
        print("✅ Label encoder loaded")
        
        # Load label mapping
        label_mapping_path = os.path.join(self.base_dir, 'label_mapping.json')
        if not os.path.exists(label_mapping_path):
            raise FileNotFoundError(f"Label mapping not found: {label_mapping_path}")
        
        with open(label_mapping_path, 'r', encoding='utf-8') as f:
            self.label_mapping = json.load(f)
        print("✅ Label mapping loaded")
        
        # Load romaji mapping
        romaji_path = os.path.join(self.base_dir, 'char_to_romaji.json')
        if not os.path.exists(romaji_path):
            raise FileNotFoundError(f"Romaji mapping not found: {romaji_path}")
        
        with open(romaji_path, 'r', encoding='utf-8') as f:
            self.char_to_romaji = json.load(f)
        print("✅ Romaji mapping loaded")
        
        print(f"✅ Model initialized. Number of classes: {len(self.label_encoder['index_to_char'])}")
        print(f"📚 Characters recognized: {list(self.label_encoder['index_to_char'].values())}")
    
    def preprocess_drawing(self, image_data):
        """
        Preprocess drawing from canvas for 28x28 model
        """
        # Convert base64 to image
        if isinstance(image_data, str):
            # Remove data URL prefix if present
            if ',' in image_data:
                image_data = image_data.split(',')[1]
            
            # Decode base64
            image_bytes = base64.b64decode(image_data)
            image = Image.open(BytesIO(image_bytes))
        else:
            image = Image.fromarray(image_data)
        
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Convert to numpy array
        img_array = np.array(image)
        
        # Invert colors (canvas is white background, black drawing)
        img_array = 255 - img_array
        
        # Apply threshold to make lines clearer
        _, binary = cv2.threshold(img_array, 25, 255, cv2.THRESH_BINARY)
        
        # Find contours to extract character
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Get bounding box of all contours
            all_contours = np.vstack(contours)
            x, y, w, h = cv2.boundingRect(all_contours)
            
            # Add small padding
            padding = 5
            x = max(0, x - padding)
            y = max(0, y - padding)
            w = min(img_array.shape[1] - x, w + 2 * padding)
            h = min(img_array.shape[0] - y, h + 2 * padding)
            
            # Crop to character
            cropped = img_array[y:y+h, x:x+w]
            
            # Create square canvas
            size = 28
            max_dim = max(w, h)
            scale = size / max_dim
            new_h, new_w = int(h * scale), int(w * scale)
            
            # Resize maintaining aspect ratio
            resized = cv2.resize(cropped, (new_w, new_h))
            
            # Create square image with padding
            square = np.zeros((size, size), dtype=np.uint8)
            
            # Center the character
            y_offset = (size - new_h) // 2
            x_offset = (size - new_w) // 2
            square[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
        else:
            # If no contours found, resize the entire image
            square = cv2.resize(img_array, (28, 28))
        
        # Normalize
        final_image = square.astype('float32') / 255.0
        
        return final_image
    
    def predict(self, image_data, target_char=None):
        """
        Predict character from drawing
        """
        try:
            # Preprocess the drawing
            processed_image = self.preprocess_drawing(image_data)
            
            # Add batch and channel dimensions
            image_input = np.expand_dims(processed_image, axis=0)  # Add batch dimension
            image_input = np.expand_dims(image_input, axis=-1)     # Add channel dimension
            
            # Predict
            predictions = self.model.predict(image_input, verbose=0)
            
            # Get top predictions
            top_3_indices = np.argsort(predictions[0])[-3:][::-1]
            top_3_confidences = predictions[0][top_3_indices]
            
            # Decode predictions
            top_3_chars = [self.label_encoder['index_to_char'][i] for i in top_3_indices]
            
            # Get the best prediction
            best_char = top_3_chars[0]
            best_confidence = float(top_3_confidences[0])
            
            # Get romaji if available
            romaji = self.char_to_romaji.get(best_char, best_char)  # Fallback to character itself
            
            # Check if correct
            is_correct = False
            if target_char:
                is_correct = (best_char == target_char)
            
            # Prepare response
            result = {
                'success': True,
                'recognized_text': best_char,
                'romaji': romaji,
                'confidence': best_confidence,
                'is_correct': is_correct,
                'message': self.get_message(is_correct, best_confidence),
                'top_predictions': [
                    {'character': char, 'confidence': float(conf), 'romaji': self.char_to_romaji.get(char, char)}
                    for char, conf in zip(top_3_chars, top_3_confidences)
                ]
            }
            
            return result
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'recognized_text': '',
                'is_correct': False
            }
    
    def get_message(self, is_correct, confidence):
        """
        Generate appropriate message based on prediction
        """
        if is_correct:
            if confidence > 0.95:
                return "🎉 Perfect! Excellent drawing!"
            elif confidence > 0.85:
                return "👍 Very good! Character recognized correctly."
            else:
                return "✅ Correct character, but could be clearer."
        else:
            if confidence > 0.7:
                return "⚠️ Close, but not quite right. Try again!"
            else:
                return "❌ Not recognized. Try drawing more clearly."

# Singleton instance
_recognizer_instance = None

def get_recognizer():
    """
    Get or create recognizer instance
    """
    global _recognizer_instance
    if _recognizer_instance is None:
        try:
            _recognizer_instance = HiraganaRecognizer()
            print("✅ Hiragana recognizer created successfully")
        except Exception as e:
            print(f"❌ Failed to create recognizer: {e}")
            _recognizer_instance = None
    return _recognizer_instance

if __name__ == "__main__":
    # Test the recognizer with actual characters from your dataset
    recognizer = HiraganaRecognizer()
    
    # Test with each character in your dataset
    test_characters = ['お', 'き', 'す', 'つ', 'な', 'は', 'ま', 'や', 'れ', 'を']
    
    for char in test_characters:
        print(f"\nTesting character: {char}")
        
        # Create a test image
        test_image = np.ones((400, 500), dtype=np.uint8) * 255
        
        # Draw the character
        font_scale = 10
        thickness = 20
        text_size = cv2.getTextSize(char, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        text_x = (500 - text_size[0]) // 2
        text_y = (400 + text_size[1]) // 2
        
        cv2.putText(test_image, char, (text_x, text_y), 
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, 0, thickness, cv2.LINE_AA)
        
        # Predict
        result = recognizer.predict(test_image, target_char=char)
        print(f"  Predicted: {result['recognized_text']} (confidence: {result['confidence']:.2%})")
        print(f"  Correct: {result['is_correct']}")
        print(f"  Message: {result['message']}")