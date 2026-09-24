import sys
import os
import json
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse

from config import config
from form_parser import (
    GoogleFormParser,
    GoogleFormData,
    FormQuestion,
    QuestionType,
    GoogleSignInRequiredError
)
from gemini_mapper import GeminiFormMapper, MappedQuestionItem
from url_builder import PrefillURLBuilder, QuestionAnswer

# Initialize FastAPI App
app = FastAPI(
    title="Google Forms AI Job Application API",
    description="Automated AI mapper for Google Forms with Gemini, Chrome Extension & Web Dashboard support.",
    version="2.0.0"
)

# Enable CORS for Chrome Extension (chrome-extension://*), localhost, and custom cloud domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HISTORY_FILE = Path(__file__).parent / "history.json"


def get_history() -> List[Dict[str, Any]]:
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history_item(item: Dict[str, Any]):
    history = get_history()
    history.insert(0, item)
    # Keep last 50 entries
    history = history[:50]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Warning: Failed to save history: {e}")


def load_profile_text(custom_profile: Optional[str] = None) -> str:
    if custom_profile and custom_profile.strip():
        return custom_profile.strip()
    profile_path = config.DEFAULT_PROFILE_PATH
    if not profile_path.exists():
        # Fallback template if profile.md does not exist yet
        return "# Master Profile\nPlease configure your profile.md or edit via Dashboard."
    with open(profile_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


# Request / Response Models
class HealthResponse(BaseModel):
    status: str
    version: str
    gemini_model: str
    profile_configured: bool
    profile_character_count: int


class ProfileUpdateRequest(BaseModel):
    content: str


class ParseFormRequest(BaseModel):
    url: Optional[str] = None
    html: Optional[str] = None
    fb_data: Optional[Any] = None
    cookies: Optional[str] = None


class FillFormRequest(BaseModel):
    url: Optional[str] = None
    html: Optional[str] = None
    fb_data: Optional[Any] = None
    job_description: Optional[str] = None
    notes: Optional[str] = None
    profile_override: Optional[str] = None
    model_override: Optional[str] = None
    cookies: Optional[str] = None


class FillFormResponse(BaseModel):
    success: bool
    title: str
    description: Optional[str]
    prefilled_url: str
    summary: str
    answers: List[QuestionAnswer]
    stats: Dict[str, int]
    file_upload_questions: List[str]
    created_at: str


# ==================== API Endpoints ====================

@app.get("/api/health", response_model=HealthResponse)
def health_check():
    profile = load_profile_text()
    return HealthResponse(
        status="ok",
        version="2.0.0",
        gemini_model=config.GEMINI_MODEL,
        profile_configured=len(profile) > 50,
        profile_character_count=len(profile)
    )


@app.get("/api/profile")
def get_profile():
    profile_path = config.DEFAULT_PROFILE_PATH
    content = load_profile_text()
    mtime = None
    if profile_path.exists():
        mtime = datetime.datetime.fromtimestamp(profile_path.stat().st_mtime).isoformat()
    return {
        "content": content,
        "path": str(profile_path.name),
        "last_modified": mtime,
        "length": len(content)
    }


@app.post("/api/profile")
def update_profile(req: ProfileUpdateRequest):
    profile_path = config.DEFAULT_PROFILE_PATH
    try:
        with open(profile_path, "w", encoding="utf-8") as f:
            f.write(req.content)
        return {
            "success": True,
            "message": "Profile updated successfully",
            "last_modified": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update profile: {e}")


@app.post("/api/parse")
def parse_form(req: ParseFormRequest):
    form_data: Optional[GoogleFormData] = None
    try:
        if req.fb_data is not None:
            form_data = GoogleFormParser.parse_raw_data(req.fb_data, base_url=req.url or "")
        elif req.html:
            form_data = GoogleFormParser.parse_html(req.html, base_url=req.url or "")
        elif req.url:
            form_data = GoogleFormParser.parse_from_url(req.url, cookies=req.cookies or config.GOOGLE_COOKIES)
        else:
            raise HTTPException(status_code=400, detail="Must provide at least one of: 'url', 'html', or 'fb_data'.")
    except GoogleSignInRequiredError as err:
        return JSONResponse(
            status_code=401,
            content={
                "error": "google_sign_in_required",
                "message": str(err),
                "solution": "Use the Chrome Extension or Bookmarklet directly while logged in to extract form data seamlessly."
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse form: {e}")

    return {
        "title": form_data.title,
        "description": form_data.description,
        "url": form_data.url,
        "questions": [q.model_dump() for q in form_data.questions],
        "stats": {
            "total": len(form_data.questions),
            "fillable": len(form_data.fillable_questions),
            "file_uploads": len(form_data.file_upload_questions)
        }
    }


@app.post("/api/fill", response_model=FillFormResponse)
def fill_form(req: FillFormRequest):
    # 1. Parse Form structure
    form_data: Optional[GoogleFormData] = None
    form_url = req.url or ""
    try:
        if req.fb_data is not None:
            form_data = GoogleFormParser.parse_raw_data(req.fb_data, base_url=form_url)
        elif req.html:
            form_data = GoogleFormParser.parse_html(req.html, base_url=form_url)
        elif req.url:
            form_data = GoogleFormParser.parse_from_url(req.url, cookies=req.cookies or config.GOOGLE_COOKIES)
        else:
            raise HTTPException(status_code=400, detail="Must provide at least one of: 'url', 'html', or 'fb_data'.")
    except GoogleSignInRequiredError as err:
        return JSONResponse(
            status_code=401,
            content={
                "error": "google_sign_in_required",
                "message": str(err),
                "solution": "The form requires Google login. Use the Chrome Extension or Bookmarklet to fill it in 1-click."
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse form structure: {e}")

    if not form_data.fillable_questions:
        raise HTTPException(status_code=400, detail="No fillable questions detected in this form.")

    # 2. Load Profile
    profile_content = load_profile_text(req.profile_override)

    # 3. Call Gemini
    try:
        mapper = GeminiFormMapper(model_name=req.model_override)
        answers = mapper.map_form(
            form_data=form_data,
            profile_content=profile_content,
            job_description=req.job_description,
            additional_notes=req.notes
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini AI mapping failed: {e}")

    # 4. Generate Pre-filled URL
    effective_base_url = form_data.url or form_url or ""
    prefilled_url = PrefillURLBuilder.build_url(
        base_url=effective_base_url,
        answers=answers
    )

    # 5. Extract file upload questions
    file_upload_titles = [q.title for q in form_data.file_upload_questions]

    # 6. Save to History
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history_record = {
        "title": form_data.title,
        "prefilled_url": prefilled_url,
        "timestamp": now_str,
        "questions_count": len(form_data.fillable_questions),
        "job_description_snippet": (req.job_description[:100] + "...") if req.job_description else "None provided",
        "has_file_upload": len(file_upload_titles) > 0
    }
    save_history_item(history_record)

    return FillFormResponse(
        success=True,
        title=form_data.title,
        description=form_data.description,
        prefilled_url=prefilled_url,
        summary=f"Successfully mapped {len(answers)} questions with Gemini.",
        answers=answers,
        stats={
            "total": len(form_data.questions),
            "fillable": len(form_data.fillable_questions),
            "file_uploads": len(form_data.file_upload_questions)
        },
        file_upload_questions=file_upload_titles,
        created_at=now_str
    )


@app.get("/api/history")
def list_history():
    return {"history": get_history()}


@app.delete("/api/history")
def clear_history():
    try:
        if HISTORY_FILE.exists():
            HISTORY_FILE.unlink()
        return {"success": True, "message": "History cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear history: {e}")


# ==================== Static / Web UI Mounting ====================

static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
def index_page():
    index_file = static_dir / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Google Forms AI API is running!</h1><p>Visit /docs for Swagger API documentation.</p>")


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    return index_page()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
