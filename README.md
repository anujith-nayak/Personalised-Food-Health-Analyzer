# Personalised Food & Health Analyzer — Live Food ML Integration

Branch: **`abhiramidk`**

This repository contains the backend and frontend for the AI-Powered Personalised Food & Health Analyzer. This document describes the **Ensemble Learning Vision System**, **Dish-to-Ingredient & Macro Mapper**, **ML Metrics API**, and complete **Integration Guide** for frontend developers.

---

## 1. How the Dish-to-Ingredient & Macro Mapping Works

When a user uploads a dish image:

1. **Ensemble Vision Classification**:
   - The image is processed in parallel across multiple Vision Transformer models (`Zodex/my-final-food-model-v29` and `dima806/indian_food_image_detection`).
   - The system selects the output prediction with the **maximum confidence score** (`max_confidence`).

2. **Ingredient & Macro Resolution Service (`backend/app/services/food_details_resolver.py`)**:
   - The identified dish name (e.g. `Dosa`, `Paneer Butter Masala`, `Idli`) is mapped against a specialized Indian dish database (`DISH_KNOWLEDGE_BASE`).
   - It extracts:
     - **Constituent Ingredients**: Exact recipe ingredients (e.g. `["Fermented Rice & Black Gram Batter", "Oil/Ghee", "Fenugreek Seeds", "Salt"]`).
     - **Nutritional Macros** (per serving):
       - `calories` (kcal)
       - `carbohydrates` (g)
       - `protein` (g)
       - `total_fat` (g)
       - `saturated_fat` (g)
       - `fiber` (g)
       - `sodium` (mg)
   - If an unlisted dish is predicted, an intelligent estimation engine infers generic macro baselines (`estimated_fallback`) so the health engine never crashes.

3. **Personalized Medical Engine Evaluation**:
   - The constituent macros and ingredients are passed into the clinical risk engine (`analyze_with_health_r`), matching against the logged-in user's health profile (Hypertension, Diabetes, PCOS, BMI, Thyroid, Heart/Kidney Disease).
   - Generates score deductions, risk rating (`Safe`, `Occasional Use`, `Moderate Risk`, `High Risk`, `Dangerous`), score explanations, and alternative food recommendations.

---

## 2. API Endpoints

### A. Live Food Identification & Health Analysis
**`POST /scan/live-food`**  
- **Headers**: `Authorization: Bearer <JWT_ACCESS_TOKEN>`
- **Body**: `multipart/form-data` with `file`: image file (`jpg`, `png`, `webp`)

#### Sample JSON Response:
```json
{
  "identified_food": "Dosa",
  "max_confidence": 0.9654,
  "selected_model": {
    "id": "model_21",
    "name": "21-Class Core Model"
  },
  "all_model_outputs": [
    {
      "model_id": "model_21",
      "model_name": "21-Class Core Model",
      "predicted_label": "Dosa",
      "confidence": 0.9654
    },
    {
      "model_id": "model_80",
      "model_name": "80-Class Sweets & Curries Model",
      "predicted_label": "Dosa",
      "confidence": 0.8821
    }
  ],
  "ingredients": [
    "Fermented Rice & Black Gram Batter",
    "Oil/Ghee",
    "Fenugreek Seeds",
    "Salt"
  ],
  "constituent_nutrition": {
    "calories": 168,
    "carbohydrates": 29,
    "protein": 3.9,
    "total_fat": 3.7,
    "saturated_fat": 0.9,
    "fiber": 1.8,
    "sodium": 220
  },
  "health_score": 85,
  "risk_level": "Safe",
  "risk_color": "green",
  "risk_advice": "This food is safe for your health conditions.",
  "score_explanation": [
    "Starting score: 100",
    "−15 pts | Hypertension: sodium = 220mg (limit 2000mg/day, 11% of daily allowance, moderate rule)",
    "Final Score: 85/100"
  ],
  "reasons": [
    "This product contains 220mg of sodium..."
  ],
  "affected_conditions": [
    "Hypertension"
  ],
  "final_recommendation": "This food is generally safe for your health profile.",
  "personalized_for": "Abhiram",
  "user_conditions": ["Hypertension"]
}
```

---

### B. Machine Learning Ensemble Evaluation Metrics
**`GET /scan/ml-metrics`**  
- **Headers**: None required (Public endpoint)

#### Sample JSON Response:
```json
{
  "ensemble_name": "Multi-Model Max Confidence Vision Classifier",
  "models": [
    {
      "id": "model_21",
      "name": "21-Class Core Model",
      "hf_repo": "Zodex/my-final-food-model-v29",
      "metrics": {
        "accuracy": 0.942,
        "top_5_accuracy": 0.988,
        "precision": 0.938,
        "recall": 0.941,
        "f1_score": 0.939
      }
    },
    {
      "id": "model_80",
      "name": "80-Class Sweets & Curries Model",
      "hf_repo": "dima806/indian_food_image_detection",
      "metrics": {
        "accuracy": 0.895,
        "top_5_accuracy": 0.962,
        "precision": 0.891,
        "recall": 0.894,
        "f1_score": 0.892
      }
    }
  ],
  "ensemble_strategy": "Maximum Confidence Selection",
  "ensemble_performance": {
    "overall_accuracy": 0.958,
    "top_3_accuracy": 0.989,
    "weighted_precision": 0.954,
    "weighted_recall": 0.958,
    "weighted_f1_score": 0.955,
    "latency_p95_ms": 320
  }
}
```

---

## 3. How Frontend Developers Should Integrate This

### Flutter Example: Calling `/scan/live-food`

```dart
import 'dart:convert';
import 'package:http/http.dart' as http;

Future<Map<String, dynamic>> scanLiveFood(String imagePath, String token) async {
  var request = http.MultipartRequest(
    'POST',
    Uri.parse('http://<YOUR_BACKEND_IP>:8000/scan/live-food'),
  );

  request.headers['Authorization'] = 'Bearer $token';
  request.files.add(await http.MultipartFile.fromPath('file', imagePath));

  var streamedResponse = await request.send();
  var response = await http.Response.fromStream(streamedResponse);

  if (response.statusCode == 200) {
    return jsonDecode(response.body);
  } else {
    throw Exception('Failed to identify food: ${response.body}');
  }
}
```

### UI Integration Recommendations:

1. **Food Card Header**:
   - Display `identified_food` with a badge showing `max_confidence` (e.g. `Dosa - 96.5% Confidence`).
   - Display `selected_model.name` as metadata.

2. **Ingredients & Macros Section**:
   - Render `ingredients` as chips/pills.
   - Render `constituent_nutrition` (Calories, Carbs, Protein, Fat, Sodium, Fiber) as a progress bar or macro card.

3. **Health Impact Badge**:
   - Display `health_score` (out of 100) with color derived from `risk_color` (`green`, `yellow`, `orange`, `red`).
   - Display `final_recommendation` text callout.

---

## 4. Git Branching & Submission Information

- Branch name: **`abhiramidk`**
- All modifications are committed to branch `abhiramidk`.
