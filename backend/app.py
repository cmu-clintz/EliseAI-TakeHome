import csv
import io
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from enrichment import enrich_lead
from scoring import score_lead

MAX_WORKERS = 5  # cap concurrent LLM calls to avoid rate limits

load_dotenv(Path(__file__).parent / ".env")

app = Flask(__name__)
CORS(app)

REQUIRED_COLUMNS = {"name", "email", "company", "address", "city", "state"}


def parse_leads_csv(file_content: str) -> tuple[list[dict], str | None]:
    """Parse CSV content into a list of lead dicts. Returns (leads, error)."""
    reader = csv.DictReader(io.StringIO(file_content))

    if reader.fieldnames is None:
        return [], "CSV file is empty or has no headers"

    headers = {h.strip().lower() for h in reader.fieldnames}
    missing = REQUIRED_COLUMNS - headers
    if missing:
        return [], f"CSV is missing required columns: {', '.join(sorted(missing))}"

    leads = []
    for i, row in enumerate(reader, start=2):  # start=2 because row 1 is header
        lead = {k.strip().lower(): v.strip() for k, v in row.items()}
        if not lead.get("email"):
            continue  # skip rows with no email
        lead["_row"] = i
        leads.append(lead)

    if not leads:
        return [], "CSV has no valid lead rows"

    return leads, None


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/process", methods=["POST"])
def process_leads():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file.filename.endswith(".csv"):
        return jsonify({"error": "File must be a CSV"}), 400

    try:
        content = file.read().decode("utf-8")
    except UnicodeDecodeError:
        return jsonify({"error": "Could not read file — make sure it is UTF-8 encoded"}), 400

    leads, error = parse_leads_csv(content)
    if error:
        return jsonify({"error": error}), 400

    def process_one(lead):
        enriched = enrich_lead(lead)
        enriched["scoring"] = score_lead(enriched)
        return enriched

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_one, lead): lead["_row"] for lead in leads}
        results = [None] * len(leads)
        for future in as_completed(futures):
            row_num = futures[future]
            idx = next(i for i, l in enumerate(leads) if l["_row"] == row_num)
            results[idx] = future.result()

    return jsonify({
        "status": "scored",
        "count": len(results),
        "leads": results,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
