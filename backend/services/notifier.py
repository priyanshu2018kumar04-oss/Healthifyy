"""
Email (Gmail SMTP) + WhatsApp (Twilio) notification service.
All functions are fail-safe — if credentials are missing they log and return False.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

APP_NAME    = os.getenv("APP_NAME", "Healthify")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5500")

# ─── Email ────────────────────────────────────────────────────────────────────

def _send_email(to_email: str, subject: str, html_body: str) -> bool:
    smtp_server   = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port     = int(os.getenv("SMTP_PORT", "587"))
    smtp_email    = os.getenv("SMTP_EMAIL", "")
    smtp_password = os.getenv("SMTP_PASSWORD", "")

    if not smtp_email or not smtp_password or smtp_email == "your_email@gmail.com":
        print("[Notifier] Email not configured — skipping email send.")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"]    = f"{APP_NAME} AI <{smtp_email}>"
        msg["To"]      = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.sendmail(smtp_email, to_email, msg.as_string())
        print(f"[Notifier] Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"[Notifier] Email error: {e}")
        return False


# ─── WhatsApp ─────────────────────────────────────────────────────────────────

def _send_whatsapp(to_phone: str, message: str) -> bool:
    account_sid   = os.getenv("TWILIO_ACCOUNT_SID", "")
    auth_token    = os.getenv("TWILIO_AUTH_TOKEN", "")
    from_number   = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

    if not account_sid or account_sid.startswith("ACxx"):
        print("[Notifier] Twilio not configured — skipping WhatsApp send.")
        return False

    # Normalise the target number
    to_wa = f"whatsapp:{to_phone}" if not to_phone.startswith("whatsapp:") else to_phone

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        client.messages.create(body=message, from_=from_number, to=to_wa)
        print(f"[Notifier] WhatsApp sent to {to_phone}")
        return True
    except Exception as e:
        print(f"[Notifier] WhatsApp error: {e}")
        return False


# ─── HTML Email Templates ─────────────────────────────────────────────────────

def _email_header(title: str, subtitle: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  body{{font-family:'Segoe UI',Arial,sans-serif;margin:0;padding:0;background:#0f172a;color:#f8fafc}}
  .wrap{{max-width:620px;margin:0 auto;padding:20px}}
  .card{{background:#1e293b;border-radius:16px;padding:24px;margin-bottom:16px;border:1px solid #334155}}
  .header{{background:linear-gradient(135deg,#7c3aed,#06b6d4);border-radius:16px;padding:32px;text-align:center;margin-bottom:16px}}
  .header h1{{color:#fff;margin:0;font-size:26px}}
  .header p{{color:rgba(255,255,255,.85);margin:6px 0 0}}
  .badge{{display:inline-block;padding:4px 12px;border-radius:99px;font-size:12px;font-weight:bold}}
  .critical{{background:#7f1d1d;color:#fca5a5}} .high{{background:#7c2d12;color:#fdba74}}
  .moderate{{background:#713f12;color:#fde68a}} .info{{background:#1e3a5f;color:#93c5fd}}
  .warn-card{{border-left:4px solid;padding:14px;margin:10px 0;border-radius:0 8px 8px 0;background:#0f172a}}
  .warn-card.critical{{border-color:#ef4444}} .warn-card.high{{border-color:#f97316}}
  .warn-card.moderate{{border-color:#f59e0b}} .warn-card.info{{border-color:#3b82f6}}
  h2,h3{{color:#e2e8f0;margin-top:0}} p{{color:#94a3b8;line-height:1.6}}
  .metric{{display:inline-block;background:#0f172a;border-radius:8px;padding:10px 16px;margin:6px}}
  .metric .val{{font-size:22px;font-weight:bold;color:#7c3aed}} .metric .lbl{{font-size:11px;color:#64748b}}
  .btn{{display:inline-block;padding:12px 28px;background:linear-gradient(135deg,#7c3aed,#06b6d4);color:#fff;text-decoration:none;border-radius:8px;font-weight:bold;margin-top:12px}}
  .footer{{text-align:center;color:#475569;font-size:12px;margin-top:24px}}
</style></head>
<body><div class="wrap">
<div class="header"><h1>🏥 {APP_NAME}</h1><p>{subtitle}</p></div>"""

def _email_footer() -> str:
    return f"""<div class="footer">
  <p>© {APP_NAME} AI · Your Personal Health Agent</p>
  <p>⚕️ This report is AI-generated. Always consult a qualified doctor for medical decisions.</p>
</div></div></body></html>"""


def build_daily_email(user_name: str, warnings: List[dict], diet_plan: dict, workout_plan: dict) -> str:
    """HTML body for the daily health report email."""
    html = _email_header("Daily Health Report", f"Good morning, {user_name}! Here's your plan for today.")

    # Warnings section
    if warnings:
        critical_count = sum(1 for w in warnings if w["level"] in ("critical", "high"))
        html += f'<div class="card"><h2>⚠️ Health Alerts ({len(warnings)} active)</h2>'
        for w in warnings:
            lvl = w.get("level", "info")
            html += f"""<div class="warn-card {lvl}">
              <strong>{w.get('title','')}</strong>
              <p style="margin:6px 0">{w.get('message','')}</p>
              <p style="margin:4px 0;font-style:italic;color:#94a3b8">➡ {w.get('action','')}</p>
            </div>"""
        html += "</div>"
    else:
        html += '<div class="card"><h2 style="color:#10b981">✅ All Health Metrics Normal</h2><p>No active health alerts today. Keep up the great work!</p></div>'

    # Diet summary
    macros = diet_plan.get("macros", {})
    html += f"""<div class="card">
      <h2>🍽️ Today's Diet Plan</h2>
      <div style="text-align:center;margin:12px 0">
        <div class="metric"><div class="val">{int(diet_plan.get('calorie_target', 0))}</div><div class="lbl">CALORIES</div></div>
        <div class="metric"><div class="val" style="color:#10b981">{macros.get('protein_g','?')}g</div><div class="lbl">PROTEIN</div></div>
        <div class="metric"><div class="val" style="color:#06b6d4">{macros.get('carbs_g','?')}g</div><div class="lbl">CARBS</div></div>
        <div class="metric"><div class="val" style="color:#f59e0b">{macros.get('fat_g','?')}g</div><div class="lbl">FAT</div></div>
      </div>
      <p>{diet_plan.get('ai_recommendation','View the full meal plan in the app.')}</p>
      <a href="{FRONTEND_URL}/plan.html" class="btn">View Full Meal Plan →</a>
    </div>"""

    # Workout summary
    html += f"""<div class="card">
      <h2>💪 Today's Workout</h2>
      <div style="text-align:center;margin:12px 0">
        <div class="metric"><div class="val">{workout_plan.get('duration_minutes','?')}</div><div class="lbl">MINUTES</div></div>
        <div class="metric"><div class="val" style="color:#ef4444">{workout_plan.get('total_calories_burned','?')}</div><div class="lbl">CAL BURN</div></div>
        <div class="metric"><div class="val" style="color:#8b5cf6">{workout_plan.get('difficulty_level','?').title()}</div><div class="lbl">LEVEL</div></div>
      </div>
      <p style="font-style:italic">{workout_plan.get('trainer_tips','View the full workout plan in the app.')}</p>
      <a href="{FRONTEND_URL}/plan.html" class="btn">View Workout Plan →</a>
    </div>"""

    html += _email_footer()
    return html


def build_weekly_email(user_name: str, weekly_summary: dict, warnings: List[dict]) -> str:
    """HTML body for the weekly progress report email."""
    html = _email_header("Weekly Progress Report", f"Your health journey this week, {user_name}")

    week = weekly_summary.get("week_summary", {})
    score = week.get("overall_health_score", 0)
    trend = week.get("trend", "stable")
    trend_emoji = {"improving": "📈", "stable": "➡️", "declining": "📉"}.get(trend, "➡️")
    score_color = "#10b981" if score >= 70 else "#f59e0b" if score >= 50 else "#ef4444"

    html += f"""<div class="card" style="text-align:center">
      <h2>Overall Health Score</h2>
      <div style="font-size:64px;font-weight:900;color:{score_color}">{score}</div>
      <div style="color:#64748b;font-size:14px">out of 100</div>
      <div style="margin-top:8px;font-size:18px">{trend_emoji} {trend.upper()}</div>
      <p style="color:#94a3b8;font-style:italic">{week.get('trend_explanation','')}</p>
    </div>"""

    # Achievements
    achievements = week.get("key_achievements", [])
    if achievements:
        items = "".join(f"<li>✅ {a}</li>" for a in achievements)
        html += f'<div class="card"><h3 style="color:#10b981">🏆 This Week\'s Achievements</h3><ul style="color:#94a3b8">{items}</ul></div>'

    # Concerns
    concerns = week.get("areas_of_concern", [])
    if concerns:
        items = "".join(f"<li>⚠️ {c}</li>" for c in concerns)
        html += f'<div class="card"><h3 style="color:#f59e0b">🎯 Areas to Improve</h3><ul style="color:#94a3b8">{items}</ul></div>'

    # Next week plan
    nwp = weekly_summary.get("next_week_plan", {})
    adjustments = nwp.get("dietary_adjustments", []) + nwp.get("workout_adjustments", [])
    if adjustments:
        items = "".join(f"<li>→ {a}</li>" for a in adjustments)
        html += f'<div class="card"><h3 style="color:#7c3aed">🗓️ Next Week Action Plan</h3><ul style="color:#94a3b8">{items}</ul></div>'

    # Motivational message
    msg = weekly_summary.get("motivational_message", "")
    if msg:
        html += f'<div class="card" style="border:1px solid #7c3aed"><p style="color:#c4b5fd;font-style:italic;font-size:16px;text-align:center">"{msg}"</p></div>'

    # Doctor recommendation
    if weekly_summary.get("doctor_consultation_recommended"):
        reason = weekly_summary.get("doctor_consultation_reason", "")
        html += f'<div class="card" style="border:1px solid #ef4444"><h3 style="color:#ef4444">⚕️ Doctor Consultation Recommended</h3><p>{reason}</p></div>'

    html += f'<div style="text-align:center"><a href="{FRONTEND_URL}/progress.html" class="btn">View Full Progress Report →</a></div>'
    html += _email_footer()
    return html


# ─── Public Interface ─────────────────────────────────────────────────────────

def send_daily_notifications(
    user_name: str,
    user_email: str,
    user_phone: Optional[str],
    warnings: List[dict],
    diet_plan: dict,
    workout_plan: dict,
) -> dict:
    """Send daily health plan + alerts via email and WhatsApp."""
    results = {"email": False, "whatsapp": False}

    # Email
    has_critical = any(w["level"] == "critical" for w in warnings)
    subject = (
        f"🔴 {APP_NAME} URGENT HEALTH ALERT — Action Required"
        if has_critical
        else f"🏥 {APP_NAME}: Your Daily Health Plan is Ready"
    )
    html = build_daily_email(user_name, warnings, diet_plan, workout_plan)
    results["email"] = _send_email(user_email, subject, html)

    # WhatsApp
    if user_phone:
        if warnings:
            wa_msg = f"🏥 *{APP_NAME} Alert* for {user_name}!\n\n"
            for w in warnings[:3]:                      # max 3 in WhatsApp
                wa_msg += f"{w['title']}\n{w['action']}\n\n"
        else:
            wa_msg = f"👋 Hi {user_name}! Your {APP_NAME} daily plan is ready.\n\n"
        wa_msg += (
            f"🍽️ Calories: *{diet_plan.get('calorie_target','?')} kcal*\n"
            f"💪 Workout: *{workout_plan.get('duration_minutes','?')} min* "
            f"(~{workout_plan.get('total_calories_burned','?')} kcal burn)\n\n"
            f"Open the app for details 👉 {FRONTEND_URL}"
        )
        results["whatsapp"] = _send_whatsapp(user_phone, wa_msg)

    return results


def send_weekly_notifications(
    user_name: str,
    user_email: str,
    user_phone: Optional[str],
    weekly_summary: dict,
    warnings: List[dict],
) -> dict:
    """Send weekly progress report via email and WhatsApp."""
    results = {"email": False, "whatsapp": False}

    score = weekly_summary.get("week_summary", {}).get("overall_health_score", "?")
    trend = weekly_summary.get("week_summary", {}).get("trend", "stable")
    subject = f"📊 {APP_NAME} Weekly Report: Score {score}/100 — {trend.upper()}"
    html = build_weekly_email(user_name, weekly_summary, warnings)
    results["email"] = _send_email(user_email, subject, html)

    if user_phone:
        wa_msg = (
            f"📊 *{APP_NAME} Weekly Report* for {user_name}\n\n"
            f"Health Score: *{score}/100*\nTrend: *{trend.upper()}*\n\n"
            f"💬 {weekly_summary.get('motivational_message', 'Keep going!')}\n\n"
            f"Full report 👉 {FRONTEND_URL}/progress.html"
        )
        results["whatsapp"] = _send_whatsapp(user_phone, wa_msg)

    return results


def send_warning_alert(
    user_name: str,
    user_email: str,
    user_phone: Optional[str],
    warning: dict,
) -> dict:
    """Send a single critical/high warning immediately."""
    results = {"email": False, "whatsapp": False}

    lvl = warning.get("level", "info")
    if lvl not in ("critical", "high"):
        return results

    subject = f"🚨 {APP_NAME}: {warning.get('title','Health Alert')}"
    html = _email_header("Urgent Health Alert", f"Important health alert for {user_name}")
    html += f"""<div class="card warn-card {lvl}" style="border-left-width:6px">
      <h2>{warning.get('title','')}</h2>
      <p>{warning.get('message','')}</p>
      <p style="font-style:italic">➡ <strong>Action: </strong>{warning.get('action','')}</p>
      <a href="{FRONTEND_URL}/dashboard.html" class="btn">Open {APP_NAME} App →</a>
    </div>"""
    html += _email_footer()
    results["email"] = _send_email(user_email, subject, html)

    if user_phone:
        wa_msg = (
            f"🚨 *{APP_NAME} URGENT ALERT*\n\n"
            f"{warning.get('title','')}\n\n"
            f"{warning.get('message','')}\n\n"
            f"Action: {warning.get('action','')}\n\n"
            f"Open the app: {FRONTEND_URL}"
        )
        results["whatsapp"] = _send_whatsapp(user_phone, wa_msg)

    return results
