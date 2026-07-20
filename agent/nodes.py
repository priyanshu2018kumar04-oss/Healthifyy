"""
LangGraph Agent Nodes — the processing units of the Healthify AI workflow.

Node execution order:
  START → input_processor → health_analyzer → warning_detector
        → diet_plan → workout_plan → [progress_tracker?] → END
"""

import json
import re
from typing import Any

from agent.state import AgentState
from agent.llm import get_llm
from agent.health_calc import (
    calculate_bmi,
    get_bmi_category,
    get_bmi_severity,
    calculate_bmr,
    calculate_tdee,
    get_calorie_target,
    classify_glucose,
    classify_bp,
    classify_cholesterol,
    classify_after_meal_glucose,
)


# ─── Utility ──────────────────────────────────────────────────────────────────

def _extract_json(text: str) -> dict:
    """Robustly extract the first JSON object from an LLM response string."""
    # Try direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # Strip markdown code fences
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Find the outermost {...} block
    brace = re.search(r"\{[\s\S]*\}", text, re.DOTALL)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            pass

    return {}


# ─── Node 1: Input Processor ──────────────────────────────────────────────────

def input_processor_node(state: AgentState) -> dict:
    """Compute derived health metrics from raw user input."""
    profile = state["user_profile"]
    metrics = state["health_metrics"]

    weight_kg   = float(metrics.get("weight_kg", 70))
    height_cm   = float(profile.get("height_cm", 170))
    age         = int(profile.get("age", 30))
    gender      = profile.get("gender", "male")
    activity    = profile.get("activity_level", "moderate")
    goal        = profile.get("goal", "maintain")

    bmi          = round(calculate_bmi(weight_kg, height_cm), 1)
    bmi_category = get_bmi_category(bmi)
    bmr          = round(calculate_bmr(weight_kg, height_cm, age, gender), 0)
    tdee         = round(calculate_tdee(bmr, activity), 0)
    cal_target   = round(get_calorie_target(tdee, goal), 0)

    return {
        "bmi": bmi,
        "bmi_category": bmi_category,
        "bmr": bmr,
        "tdee": tdee,
        "calorie_target": cal_target,
        "errors": [],
    }


# ─── Node 2: Health Analyzer ──────────────────────────────────────────────────

def health_analyzer_node(state: AgentState) -> dict:
    """Classify each health metric into a risk category."""
    metrics = state["health_metrics"]

    analysis: dict[str, Any] = {
        "bmi_status": get_bmi_severity(state["bmi"]),
        "glucose_status": "normal",
        "bp_status": "normal",
        "cholesterol_status": "normal",
        "post_meal_status": "normal",
    }

    # Fasting glucose
    glucose = metrics.get("blood_glucose_mmol")
    if glucose:
        analysis["glucose_status"] = classify_glucose(float(glucose))

    # Blood pressure
    sys_bp = metrics.get("blood_pressure_sys")
    dia_bp = metrics.get("blood_pressure_dia")
    if sys_bp and dia_bp:
        analysis["bp_status"] = classify_bp(int(sys_bp), int(dia_bp))

    # Cholesterol
    chol = metrics.get("cholesterol_mgdl")
    if chol:
        analysis["cholesterol_status"] = classify_cholesterol(float(chol))

    # After-meal glucose
    after = metrics.get("after_meal_glucose")
    if after:
        analysis["post_meal_status"] = classify_after_meal_glucose(float(after))

    return {"health_analysis": analysis}


# ─── Node 3: Warning Detector ─────────────────────────────────────────────────

def warning_detector_node(state: AgentState) -> dict:
    """Generate structured health warnings based on classified metrics."""
    analysis = state.get("health_analysis", {})
    metrics  = state["health_metrics"]
    bmi      = state["bmi"]
    bmi_cat  = state["bmi_category"]
    warnings = []

    # ── BMI Warnings ──────────────────────────────────────────────────────────
    if bmi < 16:
        warnings.append({
            "level": "critical", "category": "bmi",
            "title": "🔴 CRITICAL: Severely Underweight",
            "message": f"Your BMI is {bmi} ({bmi_cat}). This is a life-threatening level of underweight that can cause organ failure.",
            "action": "Seek immediate medical attention. Follow the high-calorie, nutrient-dense diet plan provided."
        })
    elif bmi < 18.5:
        warnings.append({
            "level": "high", "category": "bmi",
            "title": "⚠️ Underweight Alert",
            "message": f"Your BMI is {bmi} ({bmi_cat}). Underweight increases risk of nutritional deficiencies and weakened immunity.",
            "action": "Follow the calorie-surplus diet plan and strength training routine. Consider consulting a nutritionist."
        })
    elif bmi >= 40:
        warnings.append({
            "level": "critical", "category": "bmi",
            "title": "🔴 CRITICAL: Severe Obesity",
            "message": f"Your BMI is {bmi} ({bmi_cat}). This significantly increases risk of heart disease, diabetes, joint problems, and other conditions.",
            "action": "Consult a doctor immediately. Follow the calorie-deficit plan and low-impact exercise routine provided."
        })
    elif bmi >= 35:
        warnings.append({
            "level": "high", "category": "bmi",
            "title": "🔴 Obesity Class II Alert",
            "message": f"Your BMI is {bmi} ({bmi_cat}). This level of obesity requires medical supervision for safe weight loss.",
            "action": "Follow the calorie-deficit diet plan and exercise routine. Consult your doctor."
        })
    elif bmi >= 30:
        warnings.append({
            "level": "high", "category": "bmi",
            "title": "⚠️ Obese — Action Required",
            "message": f"Your BMI is {bmi} ({bmi_cat}). Obesity raises cardiovascular and metabolic disease risk.",
            "action": "Follow the calorie-deficit diet plan and aerobic exercise routine."
        })
    elif bmi >= 25:
        warnings.append({
            "level": "moderate", "category": "bmi",
            "title": "⚠️ Overweight Notice",
            "message": f"Your BMI is {bmi} ({bmi_cat}). You're in the overweight range — manageable with lifestyle changes.",
            "action": "Moderate diet adjustments and 30 min daily exercise can bring you to a healthy weight."
        })

    # ── Fasting Glucose Warnings ───────────────────────────────────────────────
    glucose = metrics.get("blood_glucose_mmol")
    g_status = analysis.get("glucose_status", "normal")
    if glucose:
        if g_status == "diabetic_range":
            warnings.append({
                "level": "critical", "category": "glucose",
                "title": "🔴 CRITICAL: Diabetic Range Blood Glucose",
                "message": f"Your fasting glucose is {glucose:.1f} mmol/L (≥7.0 = diabetic range). Immediate medical attention required.",
                "action": "See a doctor immediately. Strictly follow the low-GI diet plan. Avoid all sugar and refined carbs."
            })
        elif g_status == "pre_diabetic":
            warnings.append({
                "level": "high", "category": "glucose",
                "title": "⚠️ Pre-Diabetic Blood Glucose",
                "message": f"Your glucose is {glucose:.1f} mmol/L (5.6–6.9 = pre-diabetic range). Early intervention can prevent diabetes.",
                "action": "Follow the low-GI diet plan, increase physical activity, and monitor glucose weekly."
            })

    # ── Blood Pressure Warnings ────────────────────────────────────────────────
    sys_bp = metrics.get("blood_pressure_sys")
    dia_bp = metrics.get("blood_pressure_dia")
    bp_status = analysis.get("bp_status", "normal")
    if sys_bp and dia_bp:
        if bp_status == "hypertension_stage2":
            warnings.append({
                "level": "critical", "category": "blood_pressure",
                "title": "🔴 CRITICAL: Hypertension Stage 2",
                "message": f"Blood pressure {sys_bp}/{dia_bp} mmHg is dangerously high. Risk of stroke and heart attack is elevated.",
                "action": "Seek immediate medical attention. Strictly limit sodium (<1500 mg/day) and avoid strenuous exercise until cleared by a doctor."
            })
        elif bp_status == "hypertension_stage1":
            warnings.append({
                "level": "high", "category": "blood_pressure",
                "title": "⚠️ Hypertension Stage 1",
                "message": f"Blood pressure {sys_bp}/{dia_bp} mmHg is high. This increases cardiovascular risk.",
                "action": "Follow the DASH diet (low sodium, high potassium). Avoid caffeine and alcohol. Consult your doctor."
            })
        elif bp_status == "elevated":
            warnings.append({
                "level": "moderate", "category": "blood_pressure",
                "title": "⚠️ Elevated Blood Pressure",
                "message": f"Blood pressure {sys_bp}/{dia_bp} mmHg is elevated.",
                "action": "Reduce sodium, manage stress, and monitor BP regularly."
            })

    # ── Cholesterol Warnings ───────────────────────────────────────────────────
    chol = metrics.get("cholesterol_mgdl")
    chol_status = analysis.get("cholesterol_status", "normal")
    if chol:
        if chol_status == "high":
            warnings.append({
                "level": "high", "category": "cholesterol",
                "title": "🔴 High Cholesterol",
                "message": f"Cholesterol {chol:.0f} mg/dL (≥240 = high). Increases heart disease and stroke risk.",
                "action": "Follow the heart-healthy diet plan. Reduce saturated fats, increase omega-3 and fiber intake."
            })
        elif chol_status == "borderline":
            warnings.append({
                "level": "moderate", "category": "cholesterol",
                "title": "⚠️ Borderline Cholesterol",
                "message": f"Cholesterol {chol:.0f} mg/dL (200–239 = borderline high).",
                "action": "Reduce processed foods, increase fiber and healthy fats. Monitor every 3 months."
            })

    # ── Post-Meal Glucose Warnings ─────────────────────────────────────────────
    after = metrics.get("after_meal_glucose")
    post_status = analysis.get("post_meal_status", "normal")
    if after:
        if post_status == "high":
            warnings.append({
                "level": "high", "category": "post_meal",
                "title": "🔴 High Post-Meal Blood Sugar Spike",
                "message": f"Post-meal glucose {after:.1f} mmol/L (≥11.1 = significantly elevated). Indicates poor glucose regulation.",
                "action": "Walk 15–20 min after eating, avoid high-GI foods, eat smaller portions spread throughout the day."
            })
        elif post_status == "elevated":
            warnings.append({
                "level": "moderate", "category": "post_meal",
                "title": "⚠️ Elevated Post-Meal Blood Sugar",
                "message": f"Post-meal glucose {after:.1f} mmol/L (7.8–11.0 = elevated). Monitor your carbohydrate intake.",
                "action": "Choose low-GI foods, control portions, and walk after every meal."
            })

    return {"warnings": warnings}


# ─── Node 4: Diet Plan Generator ──────────────────────────────────────────────

def diet_plan_node(state: AgentState) -> dict:
    """Generate a personalised full-day diet plan via Groq LLM."""
    profile  = state["user_profile"]
    metrics  = state["health_metrics"]
    analysis = state.get("health_analysis", {})

    # Build dietary restriction notes based on health risks
    restrictions = []
    if analysis.get("glucose_status") in ("pre_diabetic", "diabetic_range"):
        restrictions.append("- DIABETIC/PRE-DIABETIC: Use only low-GI foods (GI<55). No sugar, white bread, white rice, or refined carbs. Spread carbs evenly across all meals.")
    if analysis.get("bp_status") in ("elevated", "hypertension_stage1", "hypertension_stage2"):
        restrictions.append("- HYPERTENSION: Sodium MUST be <1500 mg/day. Increase potassium (bananas, leafy greens, sweet potato). Apply DASH diet principles.")
    if analysis.get("cholesterol_status") in ("borderline", "high"):
        restrictions.append("- HIGH CHOLESTEROL: No saturated or trans fats. Prioritize omega-3 rich foods (salmon, walnuts, flaxseed), oats, and soluble fiber.")
    if state["bmi"] < 18.5:
        restrictions.append("- UNDERWEIGHT: Use calorie-dense but healthy foods. Include healthy fats, whole grains, legumes, and protein at every meal.")
    if state["bmi"] >= 30:
        restrictions.append("- OBESITY: Every meal must be low-calorie-density. High-volume vegetables, lean proteins, avoid all processed foods.")

    goal_labels = {
        "fat_loss":    "Fat Loss — calorie deficit, high protein to preserve lean muscle, high fiber for satiety",
        "weight_gain": "Healthy Weight Gain — calorie surplus with nutrient-dense whole foods, high complex carbs",
        "bodybuilding":"Bodybuilding — very high protein, timed carbs around workouts, leucine-rich foods",
        "maintain":    "Balanced Maintenance — all macros, diverse micronutrients, whole-food based",
    }
    goal = profile.get("goal", "maintain")

    prompt = f"""You are a certified nutritionist and clinical dietitian AI. Generate a complete, highly detailed daily diet plan.

PATIENT PROFILE:
- Name: {profile.get('name', 'User')}
- Age: {profile.get('age')} years | Gender: {profile.get('gender')}
- Weight: {metrics.get('weight_kg')} kg | Height: {profile.get('height_cm')} cm
- BMI: {state['bmi']} ({state['bmi_category']})
- Goal: {goal_labels.get(goal, goal)}
- Daily Calorie Target: {int(state['calorie_target'])} kcal
- TDEE (maintenance): {int(state['tdee'])} kcal
- Fasting Blood Glucose: {metrics.get('blood_glucose_mmol', 'not provided')} mmol/L
- Cholesterol: {metrics.get('cholesterol_mgdl', 'not provided')} mg/dL
- Blood Pressure: {f"{metrics.get('blood_pressure_sys')}/{metrics.get('blood_pressure_dia')} mmHg" if metrics.get('blood_pressure_sys') else 'not provided'}

HEALTH RESTRICTIONS (MUST follow all that apply):
{chr(10).join(restrictions) if restrictions else '- No specific restrictions. Focus on balanced, wholesome nutrition.'}

OUTPUT FORMAT: Return ONLY valid JSON, no other text, no markdown, no explanation:
{{
  "calorie_target": {int(state['calorie_target'])},
  "macros": {{
    "protein_g": <number>,
    "carbs_g": <number>,
    "fat_g": <number>,
    "fiber_g": <number>,
    "sodium_mg": <number>
  }},
  "meals": {{
    "breakfast": {{
      "time": "7:00 - 8:00 AM",
      "items": [
        {{
          "name": "<food name>",
          "quantity": "<e.g. 2 eggs / 150g / 1 cup>",
          "calories": <number>,
          "protein_g": <number>,
          "carbs_g": <number>,
          "fat_g": <number>,
          "gi_index": "<low|medium|high>"
        }}
      ],
      "total_calories": <number>,
      "preparation_tip": "<brief cooking tip>"
    }},
    "morning_snack": {{
      "time": "10:00 - 10:30 AM",
      "items": [...],
      "total_calories": <number>,
      "preparation_tip": "..."
    }},
    "lunch": {{
      "time": "1:00 - 2:00 PM",
      "items": [...],
      "total_calories": <number>,
      "preparation_tip": "..."
    }},
    "evening_snack": {{
      "time": "4:30 - 5:00 PM",
      "items": [...],
      "total_calories": <number>,
      "preparation_tip": "..."
    }},
    "dinner": {{
      "time": "7:30 - 8:30 PM",
      "items": [...],
      "total_calories": <number>,
      "preparation_tip": "..."
    }}
  }},
  "hydration_ml": <number>,
  "supplements": ["<name: dose and timing>"],
  "foods_to_avoid": ["<food>"],
  "grocery_list": ["<item>"],
  "dietary_notes": "<important notes for this specific patient>",
  "ai_recommendation": "<personalized 2-3 sentence recommendation>"
}}"""

    try:
        llm = get_llm(temperature=0.2)
        response = llm.invoke(prompt)
        diet_data = _extract_json(response.content)
        if not diet_data:
            diet_data = {
                "error": "Diet plan generation returned invalid JSON. Please try again.",
                "calorie_target": int(state["calorie_target"])
            }
    except Exception as e:
        diet_data = {"error": str(e), "calorie_target": int(state["calorie_target"])}

    return {"diet_plan": diet_data}


# ─── Node 5: Workout Plan Generator ──────────────────────────────────────────

def workout_plan_node(state: AgentState) -> dict:
    """Generate a personalised workout + yoga plan via Groq LLM."""
    profile  = state["user_profile"]
    metrics  = state["health_metrics"]
    warnings = state.get("warnings", [])
    include_yoga = state.get("include_yoga", True)

    # Safety check — high BP means no heavy lifting
    has_severe_bp = any(
        w["category"] == "blood_pressure" and w["level"] in ("high", "critical")
        for w in warnings
    )
    has_severe_obesity = state["bmi"] >= 35

    safety_notes = []
    if has_severe_bp:
        safety_notes.append("SAFETY: User has hypertension. Avoid any Valsalva maneuver, heavy overhead press, or maximal exertion. Keep intensity moderate (RPE ≤ 6/10).")
    if has_severe_obesity:
        safety_notes.append("SAFETY: High BMI — prefer low-impact exercises (swimming, cycling, walking, seated resistance). Avoid high-impact jumping exercises.")

    goal_labels = {
        "fat_loss":    "Fat Loss — cardio-dominant, HIIT intervals, circuit training, calorie burn priority",
        "weight_gain": "Muscle & Weight Gain — progressive overload, compound movements, strength split",
        "bodybuilding":"Bodybuilding — hypertrophy training, muscle isolation, pump-focused, time under tension",
        "maintain":    "Maintain Fitness — balanced cardio + strength + flexibility",
    }
    goal = profile.get("goal", "maintain")

    prompt = f"""You are a certified personal trainer, strength coach, and yoga instructor AI. Generate a complete daily fitness plan.

ATHLETE PROFILE:
- Name: {profile.get('name', 'User')}
- Age: {profile.get('age')} | Gender: {profile.get('gender')}
- Weight: {metrics.get('weight_kg')} kg | BMI: {state['bmi']} ({state['bmi_category']})
- Training Goal: {goal_labels.get(goal, goal)}
- Include Yoga: {include_yoga}

{chr(10).join(safety_notes) if safety_notes else '- No specific safety restrictions.'}

OUTPUT FORMAT: Return ONLY valid JSON, no other text:
{{
  "workout_type": "<e.g. HIIT + Strength / Full Body Strength / Cardio Circuit>",
  "difficulty_level": "<beginner|intermediate|advanced>",
  "duration_minutes": <total workout time>,
  "total_calories_burned": <estimated total kcal>,
  "warmup": {{
    "duration_minutes": 5,
    "exercises": [
      {{"name": "...", "duration_seconds": <number>, "description": "..."}}
    ]
  }},
  "main_workout": {{
    "exercises": [
      {{
        "name": "<exercise name>",
        "category": "<cardio|strength|flexibility>",
        "sets": <number or null>,
        "reps": "<e.g. '12' or '30 seconds' or null>",
        "rest_seconds": <number>,
        "calories_burned": <number>,
        "instructions": "<step-by-step form cue>",
        "muscles_targeted": ["<muscle>"],
        "modification_easier": "<easier version>",
        "modification_harder": "<harder version>"
      }}
    ]
  }},
  "cooldown": {{
    "duration_minutes": 5,
    "exercises": [
      {{"name": "...", "duration_seconds": <number>, "description": "..."}}
    ]
  }},
  "yoga_session": {{
    "include": {str(include_yoga).lower()},
    "duration_minutes": 15,
    "style": "<e.g. Hatha / Vinyasa / Restorative>",
    "benefits": "...",
    "poses": [
      {{
        "name": "<English name>",
        "sanskrit_name": "<Sanskrit name>",
        "duration_seconds": <number>,
        "benefits": "...",
        "instructions": "...",
        "breathing": "<inhale/exhale cue>"
      }}
    ]
  }},
  "weekly_schedule": {{
    "monday": "<workout type or rest>",
    "tuesday": "...",
    "wednesday": "...",
    "thursday": "...",
    "friday": "...",
    "saturday": "...",
    "sunday": "Active Recovery / Rest"
  }},
  "trainer_tips": "<2-3 motivational tips specific to this user>",
  "safety_reminders": ["<safety tip>"],
  "progress_metrics": ["<what to track to measure improvement>"]
}}"""

    try:
        llm = get_llm(temperature=0.2)
        response = llm.invoke(prompt)
        workout_data = _extract_json(response.content)
        if not workout_data:
            workout_data = {"error": "Workout plan generation failed. Please try again."}
    except Exception as e:
        workout_data = {"error": str(e)}

    return {"workout_plan": workout_data}


# ─── Node 6: Progress Tracker ─────────────────────────────────────────────────

def progress_tracker_node(state: AgentState) -> dict:
    """Generate a weekly health progress summary and forward plan via Groq LLM."""
    profile    = state["user_profile"]
    historical = state.get("historical_data", [])
    warnings   = state.get("warnings", [])

    # Format historical data for the prompt
    if historical:
        history_lines = "\n".join(
            f"  - {e.get('date')}: Weight={e.get('weight_kg','?')}kg, "
            f"Glucose={e.get('blood_glucose_mmol','?')} mmol/L, "
            f"Cholesterol={e.get('cholesterol_mgdl', 'N/A')} mg/dL"
            for e in historical[-7:]
        )
    else:
        history_lines = "  - No previous data — this is the first entry (baseline week)"

    critical_warnings = [w["title"] for w in warnings if w["level"] in ("critical", "high")]

    prompt = f"""You are a health monitoring and progress analysis AI. Generate a comprehensive weekly health progress report.

USER: {profile.get('name')} | Age: {profile.get('age')} | Goal: {profile.get('goal', 'maintain')}
Current BMI: {state['bmi']} ({state['bmi_category']})
Current Calorie Target: {int(state.get('calorie_target', 0))} kcal/day

WEEKLY HEALTH DATA:
{history_lines}

ACTIVE HEALTH ALERTS ({len(warnings)} total):
{chr(10).join(['  - ' + w for w in critical_warnings]) if critical_warnings else '  - None'}

OUTPUT FORMAT: Return ONLY valid JSON, no other text:
{{
  "week_summary": {{
    "overall_health_score": <number 1-100>,
    "trend": "<improving|stable|declining>",
    "trend_explanation": "...",
    "key_achievements": ["...", "..."],
    "areas_of_concern": ["...", "..."]
  }},
  "metric_analysis": {{
    "weight_trend": "<description>",
    "weight_change_kg": <number, negative = loss>,
    "glucose_trend": "<description>",
    "average_glucose_mmol": <number or null>,
    "notes": "..."
  }},
  "next_week_plan": {{
    "primary_focus": "...",
    "dietary_adjustments": ["...", "..."],
    "workout_adjustments": ["...", "..."],
    "targets": {{
      "weight_goal_kg": <number>,
      "calorie_adjustment": <number, e.g. -100 or +50>,
      "glucose_goal_mmol": <number>
    }}
  }},
  "habit_recommendations": ["...", "..."],
  "motivational_message": "<personal, uplifting message for this specific user>",
  "doctor_consultation_recommended": <true|false>,
  "doctor_consultation_reason": "<reason or empty string>"
}}"""

    try:
        llm = get_llm(temperature=0.3)
        response = llm.invoke(prompt)
        summary = _extract_json(response.content)
        if not summary:
            summary = {"error": "Weekly summary generation failed. Please try again."}
    except Exception as e:
        summary = {"error": str(e)}

    return {"weekly_summary": summary}
