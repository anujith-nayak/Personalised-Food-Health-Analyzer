import os
import logging
import asyncio
from typing import Dict, Any, List
from PIL import Image

logger = logging.getLogger(__name__)

# Cache models in memory once initialized
_MODELS_CACHE = {}

MODEL_CONFIGS = [
    {
        "id": "model_21",
        "name": "21-Class Core Model",
        "hf_repo": "Zodex/my-final-food-model-v29"
    },
    {
        "id": "model_80",
        "name": "80-Class Sweets & Curries Model",
        "hf_repo": "dima806/indian_food_image_detection"
    }
]

def _get_pipeline(hf_repo: str):
    """Lazy loader for HuggingFace vision classification pipeline."""
    if hf_repo not in _MODELS_CACHE:
        # Set cache dir to local workspace cache folder if needed
        cache_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".cache", "huggingface")
        os.environ["HF_HOME"] = cache_path
        
        from transformers import pipeline
        logger.info(f"Loading HuggingFace vision model pipeline for repo: {hf_repo}")
        _MODELS_CACHE[hf_repo] = pipeline("image-classification", model=hf_repo)
    return _MODELS_CACHE[hf_repo]

def _predict_single_model(model_cfg: Dict[str, str], image: Image.Image) -> Dict[str, Any]:
    """Run prediction on a single model and return top prediction details."""
    try:
        classifier = _get_pipeline(model_cfg["hf_repo"])
        raw_preds = classifier(image)
        if not raw_preds:
            return None
        
        # Sort predictions by score descending
        sorted_preds = sorted(raw_preds, key=lambda x: x["score"], reverse=True)
        top = sorted_preds[0]
        
        # Clean label (e.g. "aloo_gobi" -> "Aloo Gobi")
        clean_label = top["label"].replace("_", " ").title()
        
        return {
            "model_id": model_cfg["id"],
            "model_name": model_cfg["name"],
            "predicted_label": clean_label,
            "raw_label": top["label"],
            "confidence": float(top["score"]),
            "all_predictions": [
                {
                    "label": p["label"].replace("_", " ").title(),
                    "score": float(p["score"])
                }
                for p in sorted_preds[:5]
            ]
        }
    except Exception as e:
        logger.error(f"Error predicting with model {model_cfg['id']} ({model_cfg['hf_repo']}): {e}")
        return {
            "model_id": model_cfg["id"],
            "model_name": model_cfg["name"],
            "error": str(e),
            "confidence": -1.0
        }

async def classify_food_ensemble(image: Image.Image) -> Dict[str, Any]:
    """
    Runs image through all ensemble models in parallel threads to avoid blocking,
    then selects the model prediction with maximum confidence.
    """
    loop = asyncio.get_running_loop()
    tasks = [
        loop.run_in_executor(None, _predict_single_model, cfg, image)
        for cfg in MODEL_CONFIGS
    ]
    
    results = await asyncio.gather(*tasks)
    
    # Filter out errored model runs
    valid_results = [r for r in results if r and "confidence" in r and r["confidence"] >= 0]
    
    if not valid_results:
        raise ValueError("Failed to get valid predictions from ensemble models.")
    
    # Ensemble decision: Pick prediction with max confidence score
    best_prediction = max(valid_results, key=lambda x: x["confidence"])
    
    return {
        "identified_food": best_prediction["predicted_label"],
        "max_confidence": best_prediction["confidence"],
        "selected_model": {
            "id": best_prediction["model_id"],
            "name": best_prediction["model_name"]
        },
        "all_model_outputs": results
    }
