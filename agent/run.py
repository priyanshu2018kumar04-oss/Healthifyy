#!/usr/bin/env python3
"""
Standalone CLI to test the Healthify LangGraph agent without the backend.

Usage (from repo root):
  python agent/run.py

Requires GROQ_API_KEY in backend/.env
"""
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from agent.graph import health_graph


def main():
    sample_state = {
        "user_id": 0,
        "user_profile": {
            "name": "Demo User",
            "age": 28,
            "gender": "male",
            "height_cm": 175,
            "goal": "fat_loss",
            "activity_level": "moderate",
        },
        "health_metrics": {
            "weight_kg": 82,
            "blood_glucose_mmol": 5.8,
            "blood_pressure_sys": 128,
            "blood_pressure_dia": 82,
            "cholesterol_mgdl": 210,
            "after_meal_glucose": 8.2,
        },
        "historical_data": [
            {"date": "2026-07-14", "weight_kg": 83.5, "blood_glucose_mmol": 6.0, "cholesterol_mgdl": 215},
            {"date": "2026-07-17", "weight_kg": 82.8, "blood_glucose_mmol": 5.9, "cholesterol_mgdl": 212},
        ],
        "include_yoga": True,
        "generate_weekly": True,
        "bmi": 0.0,
        "bmi_category": "",
        "bmr": 0.0,
        "tdee": 0.0,
        "calorie_target": 0.0,
        "health_analysis": {},
        "warnings": [],
        "diet_plan": {},
        "workout_plan": {},
        "weekly_summary": {},
        "notifications_sent": False,
        "errors": [],
    }

    print("Running Healthify LangGraph pipeline (Groq LLaMA 3.3)...")
    result = health_graph.invoke(sample_state)

    print("\n=== BMI & Targets ===")
    print(f"BMI: {result['bmi']} ({result['bmi_category']})")
    print(f"Calorie target: {result['calorie_target']} kcal")

    print(f"\n=== Warnings ({len(result.get('warnings', []))}) ===")
    for w in result.get("warnings", []):
        print(f"  [{w['level']}] {w['title']}")

    print("\n=== Diet plan (summary) ===")
    diet = result.get("diet_plan", {})
    print(json.dumps({
        "calorie_target": diet.get("calorie_target"),
        "macros": diet.get("macros"),
        "ai_recommendation": diet.get("ai_recommendation"),
    }, indent=2))

    print("\n=== Workout plan (summary) ===")
    workout = result.get("workout_plan", {})
    print(json.dumps({
        "workout_type": workout.get("workout_type"),
        "duration_minutes": workout.get("duration_minutes"),
        "total_calories_burned": workout.get("total_calories_burned"),
    }, indent=2))

    if result.get("weekly_summary"):
        print("\n=== Weekly summary ===")
        print(json.dumps(result["weekly_summary"].get("week_summary", {}), indent=2))

    print("\nDone.")


if __name__ == "__main__":
    main()
