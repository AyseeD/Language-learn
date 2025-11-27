import numpy as np
from keras.models import load_model
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class MLService:
    _instance = None
    _model = None

    def __new__(cls, model_path: str):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, model_path: str):
        if self._model is None:
            self.load_model(model_path)

    def load_model(self, model_path: str):
        try:
            self._model = load_model(model_path)
            logger.info(f"Model loaded successfully from {model_path}")
        except Exception as e:
            logger.error(f"Failed to load model: {str(e)}")
            raise

    def predict(self, features: np.ndarray) -> Dict[str, Any]:
        try:
            if len(features.shape) == 1:
                features = features.reshape(1, -1)

            prediction = self._model.predict(features, verbose=0)
            confidence = float(np.max(prediction))
            predicted_class = int(np.argmax(prediction))

            return {
                'predicted_class': predicted_class,
                'confidence': confidence,
                'raw_prediction': prediction.tolist()
            }
        except Exception as e:
            logger.error(f"Prediction failed: {str(e)}")
            raise

    def preprocess_input(self, raw_input: list) -> np.ndarray:
        return np.array(raw_input, dtype=np.float32)