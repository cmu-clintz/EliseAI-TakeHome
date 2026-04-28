# EliseAI Take-Home — Inbound Lead Enrichment Tool

A web app that takes a CSV of inbound leads, enriches them via public APIs, scores them, and generates personalized outreach emails using Claude AI.

---

## Quick Start

You need two terminals — one for the backend, one for the frontend.

**Terminal 1 — Backend:**
```bash
cd backend
python -m venv venv
./venv/Scripts/activate      # Windows
# source venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
cp .env.example .env         # then add your ANTHROPIC_API_KEY
python app.py
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`, upload `sample_leads.csv`, and click **Process Leads**.

---

## Project Structure

```
EliseAI-TakeHome/
├── backend/
│   ├── app.py          # Flask entry point + /api/process endpoint
│   ├── enrichment.py   # U.S. Census API + Wikipedia API calls
│   ├── scoring.py      # Claude AI scoring, insights, and email generation
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   └── components/
│   │       ├── UploadPanel.jsx   # CSV drag-and-drop upload
│   │       ├── ResultsTable.jsx  # Sortable leads table
│   │       └── LeadCard.jsx      # Expanded lead detail modal
│   └── vite.config.js
├── sample_leads.csv    # 8 sample leads for testing
└── README.md
```

---

## Backend Setup (Flask)

### Requirements
- Python 3.10+

### Steps

```bash
cd backend

# Create and activate virtual environment
python -m venv venv

# Activate (Windows)
./venv/Scripts/activate
# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# Run the server
python app.py
```

The Flask server runs on `http://localhost:8080`.

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| POST | `/api/process` | Upload CSV, returns enriched + scored leads |

### CSV Format

The uploaded CSV must include these columns (case-insensitive):

| Column | Example |
|--------|---------|
| name | Sarah Johnson |
| email | sarah@example.com |
| company | Peak Properties |
| address | 1200 Market St |
| city | Philadelphia |
| state | PA |

See `sample_leads.csv` for a working example.

---

## Frontend Setup (React + Vite)

### Requirements
- Node.js 18+

### Steps

```bash
cd frontend
npm install
npm run dev
```

The React app runs on `http://localhost:5173` and proxies `/api/*` to the Flask backend on port 8080.

> Make sure the Flask backend is running before using the app.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key for scoring and email generation |
| `WALKSCORE_API_KEY` | No | WalkScore API key for property location scores — free at walkscore.com/professional/api.php |
| `RENTCAST_API_KEY` | No | RentCast API key for property type and unit count validation — free tier at rentcast.io |
