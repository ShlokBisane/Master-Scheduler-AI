"""
Master Scheduler AI — FastAPI Backend
Serves the frontend website and provides API endpoints.
"""

import os
import json
import re
from datetime import date
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import database as db
from ai_engine import (
    get_ai_response, stream_ai_response, generate_chat_title,
    extract_schedule_from_response, clean_response_text
)
from ranking_engine import (
    SubjectEntry, rank_subjects, rerank_after_missed_day,
    generate_daily_study_order, detect_exam_type, get_subject_color
)

app = FastAPI(title="Master Scheduler AI", version="2.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Request Models ─────────────────────────────────────────

class ChatMessage(BaseModel):
    content: str
    chat_id: Optional[int] = None
    mode: Optional[str] = "student"

class SettingsUpdate(BaseModel):
    gemini_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    active_provider: Optional[str] = None
    user_name: Optional[str] = None
    user_type: Optional[str] = None

class ConfirmSchedule(BaseModel):
    message_id: int
    chat_id: int
    sessions: list


class ScheduleDraftRequest(BaseModel):
    response_text: str

class TaskStatusUpdate(BaseModel):
    status: str

class NewChat(BaseModel):
    title: Optional[str] = "New Chat"
    mode: Optional[str] = "student"

class ProfileUpdate(BaseModel):
    name: Optional[str] = ""
    user_type: Optional[str] = "student"
    class_course: Optional[str] = ""
    board_university: Optional[str] = ""
    subjects: Optional[str] = ""
    daily_study_hours: Optional[str] = ""
    preferred_slots: Optional[str] = ""
    sleep_time: Optional[str] = ""
    wake_time: Optional[str] = ""
    tuition_timings: Optional[str] = ""
    coaching_timings: Optional[str] = ""
    college_timings: Optional[str] = ""
    can_study_long: Optional[str] = ""
    preferred_language: Optional[str] = ""
    voice_preference: Optional[str] = ""

class SubjectColorUpdate(BaseModel):
    subject: str
    color: str

class RankingRequest(BaseModel):
    subjects: list  # List of subject dicts with topic, exam_type, exam_date, confidence, etc.

class MissedDayRequest(BaseModel):
    subjects: list
    missed_topics: list
    available_hours: float = 4.0


# ─── Settings Endpoints ────────────────────────────────────

@app.get("/api/settings")
async def get_settings():
    settings = db.get_settings()
    if settings:
        # Mask API keys for security
        result = dict(settings)
        if result.get('gemini_api_key'):
            key = result['gemini_api_key']
            result['gemini_api_key_masked'] = key[:8] + '•' * (len(key) - 12) + key[-4:] if len(key) > 12 else '••••'
            result['has_gemini_key'] = True
        else:
            result['has_gemini_key'] = False
            result['gemini_api_key_masked'] = ''
        
        if result.get('openrouter_api_key'):
            key = result['openrouter_api_key']
            result['openrouter_api_key_masked'] = key[:8] + '•' * (len(key) - 12) + key[-4:] if len(key) > 12 else '••••'
            result['has_openrouter_key'] = True
        else:
            result['has_openrouter_key'] = False
            result['openrouter_api_key_masked'] = ''
            
        return result
    return {"error": "No settings found"}


@app.post("/api/settings")
async def update_settings(settings: SettingsUpdate):
    updates = {k: v for k, v in settings.model_dump().items() if v is not None}
    db.update_settings(**updates)
    return {"status": "ok"}


# ─── Profile Endpoints ─────────────────────────────────────

@app.get("/api/profile")
async def get_profile():
    """Get user profile data."""
    profile = db.get_profile()
    return {"profile": profile}


@app.post("/api/profile")
async def save_profile(data: ProfileUpdate):
    """Save user profile data."""
    profile_data = data.model_dump()
    db.save_profile(profile_data)
    return {"status": "ok"}


# ─── Chat Endpoints ─────────────────────────────────────────

@app.get("/api/chats")
async def list_chats():
    chats = db.get_all_chats()
    return {"chats": chats}


@app.post("/api/chats")
async def create_chat(data: NewChat):
    chat_id = db.create_chat(data.title, data.mode)
    return {"chat_id": chat_id, "title": data.title, "mode": data.mode}


@app.get("/api/chats/{chat_id}")
async def get_chat(chat_id: int):
    chat = db.get_chat(chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: int):
    db.delete_chat(chat_id)
    return {"status": "ok"}


@app.get("/api/chats/{chat_id}/messages")
async def get_messages(chat_id: int):
    messages = db.get_messages(chat_id)
    return {"messages": messages}


# ─── AI Chat Endpoint ──────────────────────────────────────

def _get_api_credentials():
    """Get active provider and API key from settings."""
    settings = db.get_settings()
    provider = settings['active_provider']
    
    if provider == 'gemini':
        api_key = settings.get('gemini_api_key', '')
    else:
        api_key = settings.get('openrouter_api_key', '')
    
    return provider, api_key


@app.post("/api/chat")
async def send_chat_message(data: ChatMessage):
    """Send a message and get AI response."""
    provider, api_key = _get_api_credentials()
    
    if not api_key:
        raise HTTPException(
            status_code=400, 
            detail=f"No API key set for {provider}. Please add your API key in the settings bar below."
        )
    
    # Get profile for context
    profile = db.get_profile()
    
    # Create chat if needed
    chat_id = data.chat_id
    is_new_chat = False
    if not chat_id:
        chat_id = db.create_chat("New Chat", data.mode)
        is_new_chat = True
    
    # Save user message
    db.add_message(chat_id, "user", data.content)
    
    # Get conversation history
    history = db.get_messages(chat_id)
    msg_list = [{"role": m["role"], "content": m["content"]} for m in history if m["role"] != "system"]
    
    try:
        # Get AI response with profile context
        response = get_ai_response(provider, api_key, msg_list, data.mode, profile)
        
        # Extract schedule if present
        schedule_data = extract_schedule_from_response(response)
        display_text = clean_response_text(response) if schedule_data else response
        
        # Save AI response
        msg_id = db.add_message(chat_id, "assistant", display_text, schedule_data)
        
        # Auto-name chat if it's the first message
        if is_new_chat:
            try:
                title = generate_chat_title(provider, api_key, data.content)
                db.update_chat_title(chat_id, title)
            except:
                # Use first few words as fallback
                title = " ".join(data.content.split()[:5])
                db.update_chat_title(chat_id, title)
        
        chat = db.get_chat(chat_id)
        
        return {
            "chat_id": chat_id,
            "chat_title": chat["title"] if chat else "New Chat",
            "message_id": msg_id,
            "response": display_text,
            "schedule": schedule_data,
            "provider": provider
        }
        
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "403" in error_msg:
            raise HTTPException(status_code=401, detail=f"Invalid API key for {provider}. Please check your key.")
        elif "429" in error_msg:
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait a moment and try again.")
        else:
            raise HTTPException(status_code=500, detail=f"AI Error: {error_msg}")


@app.post("/api/chat/stream")
async def stream_chat_message(data: ChatMessage):
    """Send a message and stream AI response via SSE."""
    provider, api_key = _get_api_credentials()
    
    if not api_key:
        raise HTTPException(status_code=400, detail=f"No API key set for {provider}. Please add your API key in the settings bar below.")
    
    # Get profile for context
    profile = db.get_profile()
    
    chat_id = data.chat_id
    is_new_chat = False
    if not chat_id:
        chat_id = db.create_chat("New Chat", data.mode)
        is_new_chat = True
    
    db.add_message(chat_id, "user", data.content)
    
    history = db.get_messages(chat_id)
    msg_list = [{"role": m["role"], "content": m["content"]} for m in history if m["role"] != "system"]
    
    async def event_generator():
        full_response = ""
        try:
            # Send chat_id first
            yield f"data: {json.dumps({'type': 'meta', 'chat_id': chat_id})}\n\n"
            
            for chunk in stream_ai_response(provider, api_key, msg_list, data.mode, profile):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
            
            # Process complete response
            schedule_data = extract_schedule_from_response(full_response)
            display_text = clean_response_text(full_response) if schedule_data else full_response
            
            msg_id = db.add_message(chat_id, "assistant", display_text, schedule_data)
            
            # Auto-name
            chat_title = "New Chat"
            if is_new_chat:
                try:
                    chat_title = generate_chat_title(provider, api_key, data.content)
                    db.update_chat_title(chat_id, chat_title)
                except:
                    chat_title = " ".join(data.content.split()[:5])
                    db.update_chat_title(chat_id, chat_title)
            else:
                chat = db.get_chat(chat_id)
                chat_title = chat["title"] if chat else "New Chat"
            
            # Send final metadata
            yield f"data: {json.dumps({'type': 'done', 'message_id': msg_id, 'chat_id': chat_id, 'chat_title': chat_title, 'schedule': schedule_data})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ─── Schedule Endpoints ────────────────────────────────────

@app.post("/api/schedule/confirm")
async def confirm_schedule(data: ConfirmSchedule):
    """Confirm a proposed schedule — save sessions to DB."""
    db.confirm_schedule_message(data.message_id)
    
    saved = []
    for session in data.sessions:
        sid = db.add_schedule(
            chat_id=data.chat_id,
            subject=session.get("subject", ""),
            color=session.get("color", "#4A90D9"),
            date_str=session.get("date", ""),
            start_time=session.get("start_time", ""),
            end_time=session.get("end_time", ""),
            session_type=session.get("type", "study"),
            topic=session.get("topic", ""),
            priority=session.get("priority", 3)
        )
        saved.append(sid)
    
    return {"status": "ok", "saved_count": len(saved)}


@app.post("/api/schedule/draft")
async def draft_schedule(data: ScheduleDraftRequest):
    """Parse a raw AI response and return any embedded schedule draft."""
    schedule_data = extract_schedule_from_response(data.response_text)
    if not schedule_data:
        raise HTTPException(status_code=400, detail="No schedule draft found in response text.")

    return {
        "schedule": schedule_data,
        "display_text": clean_response_text(data.response_text),
    }


@app.delete("/api/schedule/subject/{subject}")
async def delete_schedule_subject(subject: str):
    """Delete all schedules for a specific subject."""
    db.delete_schedules_by_subject(subject)
    return {"status": "ok", "detail": f"All schedules for {subject} deleted"}


@app.delete("/api/schedule/{schedule_id}")
async def delete_schedule_by_id(schedule_id: int):
    """Delete a specific schedule entry by ID."""
    db.delete_schedule_by_id(schedule_id)
    return {"status": "ok", "detail": "Schedule deleted"}


@app.delete("/api/schedule/date/{date_str}/subject/{subject}")
async def delete_schedule_by_date_and_subject(date_str: str, subject: str):
    """Delete all schedules for a specific subject on a specific date."""
    db.delete_schedule_by_date_and_subject(date_str, subject)
    return {"status": "ok", "detail": f"Schedule for {subject} on {date_str} deleted"}


@app.get("/api/schedule/calendar")
async def get_calendar():
    """Get all calendar events grouped by date."""
    events = db.get_calendar_events()
    colors = db.get_subject_colors()
    return {"calendar": events, "subject_colors": colors}


@app.get("/api/schedule/date/{date_str}")
async def get_schedule_for_date(date_str: str):
    """Get all sessions for a specific date."""
    sessions = db.get_schedules_for_date(date_str)
    return {"date": date_str, "sessions": sessions}


@app.get("/api/todo/today")
async def get_today_tasks():
    """Get today's tasks with full context."""
    result = db.get_today_tasks()
    result["date"] = date.today().isoformat()
    return result


@app.patch("/api/todo/{task_id}")
async def update_task(task_id: int, data: TaskStatusUpdate):
    """Update a task's status."""
    db.update_task_status(task_id, data.status)
    return {"status": "ok"}


def _get_health_payload():
    """Get the health/stress payload used by the sidebar meter."""
    return db.get_stress_data()


@app.get("/api/health")
async def get_health():
    """Get overall health metrics."""
    return _get_health_payload()


@app.get("/api/health/stress")
async def get_stress():
    """Get stress meter data."""
    return _get_health_payload()


# ─── Subject Colors ─────────────────────────────────────────

@app.get("/api/subject-colors")
async def get_subject_colors():
    """Get all subject color mappings."""
    colors = db.get_subject_colors()
    return {"colors": colors}


@app.post("/api/subject-colors")
async def update_subject_color_endpoint(data: SubjectColorUpdate):
    """Update a subject's color globally (affects all past and future schedules)."""
    db.update_subject_color(data.subject, data.color)
    return {"status": "ok"}


# ─── Ranking Engine Endpoints ──────────────────────────────

@app.post("/api/ranking/compute")
async def compute_ranking(data: RankingRequest):
    """Compute priority ranking for given subjects."""
    entries = []
    for subj in data.subjects:
        entry = SubjectEntry(
            subject=subj.get("subject", "Unknown"),
            topic=subj.get("topic", subj.get("subject", "Unknown")),
            exam_type=subj.get("exam_type", detect_exam_type(subj.get("subject", ""))),
            exam_date=subj.get("exam_date", ""),
            user_confidence=subj.get("confidence", 5),
            revision_status=subj.get("revision_status", "needs_revision"),
            user_priority=subj.get("priority", "medium"),
            estimated_hours=subj.get("estimated_hours", 2.0),
            color=subj.get("color", get_subject_color(subj.get("subject", ""))),
        )
        entries.append(entry)
    
    result = rank_subjects(entries)
    return result


@app.post("/api/ranking/missed-day")
async def handle_missed_day(data: MissedDayRequest):
    """Re-rank subjects after a missed study day."""
    entries = []
    for subj in data.subjects:
        entry = SubjectEntry(
            subject=subj.get("subject", "Unknown"),
            topic=subj.get("topic", subj.get("subject", "Unknown")),
            exam_type=subj.get("exam_type", "school"),
            exam_date=subj.get("exam_date", ""),
            user_confidence=subj.get("confidence", 5),
            revision_status=subj.get("revision_status", "needs_revision"),
            user_priority=subj.get("priority", "medium"),
            estimated_hours=subj.get("estimated_hours", 2.0),
        )
        entries.append(entry)
    
    result = rerank_after_missed_day(entries, data.missed_topics, data.available_hours)
    return result


# ─── Serve Frontend ─────────────────────────────────────────

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

# Mount static files
if os.path.exists(FRONTEND_DIR):
    app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
    app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")
    assets_dir = os.path.join(FRONTEND_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve the main index.html."""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Frontend not found</h1>", status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
