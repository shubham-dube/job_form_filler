# FormFiller AI - Cloud Deployment Guide

FormFiller AI is built with FastAPI and is 100% containerized and cloud-ready. You can deploy it to any free or low-cost cloud provider in under 5 minutes.

Once deployed, your API and Web Dashboard will be available 24/7 on the internet, accessible from any device (phone, laptop, iPad), and your Chrome Extension can connect to it seamlessly.

---

## Option 1: Render (Recommended - 100% Free)

1. Push this repository to your GitHub account (private or public).
2. Go to [Render.com](https://render.com) and sign in.
3. Click **New +** &rarr; **Blueprint** (or **Web Service**).
4. Connect your GitHub repository.
5. Render will automatically detect `render.yaml`:
   - **Environment**: Python 3.11
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api:app --host 0.0.0.0 --port $PORT`
6. Under **Environment Variables**, set:
   - `GEMINI_API_KEY`: Your Gemini API key from [Google AI Studio](https://aistudio.google.com/)
   - `GEMINI_MODEL`: `gemini-2.5-flash`
7. Click **Apply / Create Web Service**.
8. Once built, Render will give you a public URL (e.g. `https://formfiller-ai.onrender.com`).
9. Visit your URL to see your live Web Dashboard!

---

## Option 2: Google Cloud Run (Serverless, Generous Free Tier)

If you have a Google Cloud account, you can deploy with Google Cloud Run in 1 command:

```bash
# Build & deploy container directly to Cloud Run
gcloud run deploy formfiller-ai \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY="your_api_key_here",GEMINI_MODEL="gemini-2.5-flash"
```

Cloud Run will output your live URL (e.g. `https://formfiller-ai-xyz-uc.a.run.app`).

---

## Option 3: Railway

1. Go to [Railway.app](https://railway.app).
2. Click **New Project** &rarr; **Deploy from GitHub repo**.
3. Select your `Job_Form_Filler` repository.
4. Add Environment Variable:
   - `GEMINI_API_KEY`: your key
5. Railway will automatically build the `Dockerfile` and generate a live domain!

---

## Option 4: Localhost / Docker (Running on your PC)

You can run FormFiller AI on your local machine anytime:

### Using Python directly:
```powershell
.venv\Scripts\Activate.ps1
uvicorn api:app --reload --port 8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

### Using Docker Compose:
```bash
docker compose up -d
```

---

## Connecting the Chrome Extension to your Cloud Server

Once your cloud service is deployed:
1. Click the **FormFiller AI** icon in Chrome.
2. Click the gear icon (**⚙️ Settings**) in the top right.
3. In the **Backend Server URL** box, replace `http://localhost:8000` with your cloud URL:
   ```
   https://formfiller-ai.onrender.com
   ```
4. Click **Test Connection** &rarr; **Save Settings**.
5. Done! You can now apply to any job Google Form from any browser tab with 1-click!

---

## Mobile Usage (iPhone / Android)

1. Open your deployed Cloud Web Dashboard on your phone: `https://your-app.onrender.com`.
2. Go to the **Mobile Bookmarklet** tab.
3. Follow the instructions to install the **"✨ Fill Form"** bookmarklet.
4. Whenever you open a job application Google Form on your phone, tap your bookmarklet to automatically fill and review answers!
