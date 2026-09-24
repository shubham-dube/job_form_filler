# Google Forms AI Job Application Auto-Filler (FormFiller AI)

An end-to-end AI ecosystem that automatically maps your master profile and a targeted job description onto Google Forms application questions using **Google's Gemini API** (`google-genai` SDK) — generating an official, pre-filled Google Forms review link.

**No more manual HTML saving. No more terminal commands. 1-Click zero-friction workflow.**

---

## 🌟 Key Capabilities

1. **Chrome Extension (Manifest V3)**:
   - Fills Google Forms directly in your active browser where you are **already signed in**.
   - Extracts internal form data in milliseconds — **zero HTML file saving, zero cookie copying, zero authentication hurdles**.
   - 1-click auto-fill and auto-redirect to the official pre-filled form URL.
2. **Cloud API & Web Dashboard**:
   - Modern FastAPI backend deployable on Render, Railway, Fly.io, or Google Cloud Run.
   - Sleek dark-mode glassmorphic Web Dashboard accessible from **any device (PC, Mac, iPhone, Android)**.
   - Master Profile Studio: live visual editor to manage your resume, contact info, CTC, notice period, and project stories.
3. **Universal Mobile Bookmarklet**:
   - Apply on mobile (iPhone Safari, Android Chrome) with 1 tap.
4. **Context-Aware Reasoning with Gemini**:
   - Free-text narrative questions (*"Why do you want to join us?"*, *"Describe a challenging project"*) are dynamically tailored by Gemini combining your actual achievements with the specific Job Description (JD).
5. **Trustworthy 1-Click Review**:
   - Generates Google's official pre-filled URL (`.../viewform?usp=pp_url&entry.123=...`).
   - Displays confidence badges (`HIGH`, `MEDIUM`, `LOW`) and reasoning for every answer.
   - Lets you inspect answers and attach your resume PDF before submitting with peace of mind.

---

## 📁 Repository Structure

```
Job_Form_Filler/
├── api.py                 # FastAPI REST server exposing /api/fill, /api/profile, etc.
├── static/                # Modern Web Dashboard (HTML, CSS, JS)
│   ├── index.html
│   ├── style.css
│   └── app.js
├── extension/             # Chrome Extension (Manifest V3)
│   ├── manifest.json
│   ├── content.js         # Auto-extracts form data from active tab & floating widget
│   ├── content.css
│   ├── popup.html         # Sleek popup UI
│   ├── popup.js
│   ├── popup.css
│   ├── options.html       # Server URL & settings
│   ├── options.js
│   ├── background.js
│   └── icons/
├── profile.md             # Your master resume, standard answer bank, and logistics
├── config.py              # Configuration loader & environment validator
├── form_parser.py         # Google Forms HTML parser & FB_PUBLIC_LOAD_DATA_ extractor
├── gemini_mapper.py       # Gemini API client with Pydantic structured output
├── url_builder.py         # Query encoder for pre-filled Google Form URLs
├── main.py                # Rich CLI interface (for terminal users)
├── Dockerfile             # Multi-stage production container
├── docker-compose.yml     # 1-command local container orchestration
├── render.yaml            # 1-click cloud deployment blueprint for Render
├── DEPLOYMENT.md          # Step-by-step cloud deployment instructions
├── requirements.txt       # Dependencies (FastAPI, Uvicorn, google-genai, etc.)
└── tests/                 # Comprehensive test suite (14 unit tests)
```

---

## 🚀 Quickstart Guide

### 1. Setup Virtual Environment & Install Dependencies

```powershell
# Create virtual environment (if not already created)
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### 2. Configure Your Gemini API Key

Copy `.env.example` to `.env` (if not done):
```powershell
cp .env.example .env
```
Ensure your Gemini API key is set in `.env`:
```ini
GEMINI_API_KEY=AIzaSy...your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```
*(Get a free API key from [Google AI Studio](https://aistudio.google.com/)).*

### 3. Launch the Server & Web Dashboard

```powershell
uvicorn api:app --reload --port 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser!

---

## 🧩 Installing the Chrome Extension (30 Seconds)

1. Open Google Chrome (or Edge, Brave, Kiwi).
2. Go to `chrome://extensions` in your address bar.
3. Turn on the **Developer mode** toggle in the top-right corner.
4. Click **Load unpacked**.
5. Select the `extension/` folder inside this project directory:
   ```
   d:\Projects\Job_Form_Filler\extension
   ```
6. Pin the extension to your toolbar.
7. Now open any Google Form job application in Chrome — the extension automatically detects the form, lets you paste a Job Description, and auto-fills it with 1 click!

---

## 📱 Mobile Bookmarklet (iPhone & Android)

1. Open your Web Dashboard (`http://localhost:8000` or your deployed Cloud URL) on your phone.
2. Navigate to the **Mobile Bookmarklet** tab.
3. Copy the Bookmarklet code and save it as a bookmark named **"✨ Fill Form"**.
4. Whenever you open a Google Form on mobile, tap your bookmark to auto-fill the form!

---

## ☁️ Cloud Deployment (Render, Cloud Run, Railway)

To deploy FormFiller AI on the cloud so you can use it 24/7 from anywhere:
- See the complete step-by-step guide in [DEPLOYMENT.md](file:///d:/Projects/Job_Form_Filler/DEPLOYMENT.md).
- Ready for 1-click deploy to Render via `render.yaml` or Google Cloud Run.

---

## 🧪 Running the Test Suite

Run all 14 unit tests anytime:
```powershell
.venv\Scripts\python -m unittest discover tests
```
