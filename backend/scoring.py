import json
import os
import anthropic

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


SYSTEM_PROMPT = """
You are a lead scoring assistant for EliseAI, an AI company that automates leasing conversations
for multifamily residential property managers. EliseAI's product helps property management
companies handle inbound renter inquiries, schedule tours, and follow up with prospects — entirely
through AI. Their ideal customer is a property management company overseeing a significant
portfolio of apartment units in markets with strong rental demand.

## Scoring Rubric (100 points total)

Score each dimension using ONLY the data provided. If a data point is missing or null, score
that dimension at 0 and note it in the reason.

### 1. Market Size (20 pts) — based on city population
- > 1,000,000: 20 pts (major metro, large multifamily inventory)
- 250,000-1,000,000: 14 pts (mid-size city, strong market)
- 50,000-250,000: 8 pts (smaller but viable)
- < 50,000 or missing: 0 pts (too small or unknown)

### 2. Rental Market Strength (20 pts) — based on renter_occupied_pct
- > 55%: 20 pts (dense rental market, high leasing volume)
- 45-55%: 15 pts (strong rental market)
- 30-45%: 10 pts (moderate rental demand)
- < 30% or missing: 0 pts (mostly homeowners, weak multifamily market)

### 3. Income Fit (20 pts) — based on median_household_income
EliseAI's best-fit customers manage workforce and Class B/C multifamily housing.
- $40,000-$85,000: 20 pts (workforce housing sweet spot)
- $85,000-$110,000: 13 pts (upper-middle, still good fit)
- > $110,000: 6 pts (likely luxury market, different buying behavior)
- < $40,000: 6 pts (may have budget constraints)
- Missing: 0 pts

### 4. Property Location (20 pts) — based on WalkScore data for the managed building
The address provided is the apartment building the lead manages. High walkability and transit
access means more renters want to live there, which drives higher leasing inquiry volume —
the exact workload EliseAI automates. Score using the higher of Walk Score or Transit Score.
- Walk or Transit Score > 70: 20 pts (high-demand urban location, strong leasing volume)
- Walk or Transit Score 50-70: 14 pts (good location, solid rental demand)
- Walk or Transit Score 25-50: 7 pts (moderate, car-dependent area)
- Walk or Transit Score < 25 or missing: 0 pts (low demand, low leasing volume)

### 5. Company Profile (20 pts) — use your judgment on the company name and email domain
Points are additive. Email domain is the primary signal — many legitimate PM companies use
branded names (e.g. "Greystar", "Camden", "Aimco") with no descriptive keywords at all.

Email domain signals (primary, max 15 pts):
- Uses a company domain (not gmail/yahoo/hotmail/outlook/icloud or other free providers): +10 pts
- Email domain aligns with the company name
  (greystar.com ↔ Greystar, peakproperties.com ↔ Peak Properties,
  sunrisemgmt.com ↔ Sunrise Management — abbreviations and partial matches count): +5 pts

Company name signals (secondary, max 5 pts):
- Name contains any PM or real estate keyword
  ("management", "apartments", "residential", "housing", "realty", "properties",
  "equity", "holdings", "partners", "capital", "group", "living", "homes"): +5 pts
- No recognizable keywords: 0 pts additional — do not deduct from domain score

A lead with a strong company domain and consistent naming should score near the maximum
even without descriptive name keywords.

## Address Validation (RentCast) — not scored, controls red_flag only

RentCast is used solely to verify the address is a real rentable property. Do not factor this
into any of the 5 scored dimensions above.

- If RentCast property is NOT FOUND or has no property type: set red_flag=true,
  red_flag_reason="Address not found in RentCast — verify this is a real rental property."
- If RentCast returned a property type: set red_flag=false, red_flag_reason=null.
- If RentCast was not checked (no API key): set red_flag=false, red_flag_reason=null.

## Output Format

Respond with ONLY a valid JSON object — no markdown fences, no commentary outside the JSON.

{
  "score": <integer 0-100>,
  "red_flag": <true | false>,
  "red_flag_reason": "<one sentence if red_flag is true, else null>",
  "score_breakdown": {
    "market_size":       { "points": <int>, "max": 20, "reason": "<one sentence>" },
    "rental_market":     { "points": <int>, "max": 20, "reason": "<one sentence>" },
    "income_fit":        { "points": <int>, "max": 20, "reason": "<one sentence>" },
    "property_location": { "points": <int>, "max": 20, "reason": "<one sentence>" },
    "company_profile":   { "points": <int>, "max": 20, "reason": "<one sentence>" }
  },
  "priority": "<Hot | Warm | Cold>",
  "insights": [
    "<insight 1: a specific, actionable data point the rep should know before the call>",
    "<insight 2>",
    "<insight 3>"
  ],
  "outreach_email": {
    "subject": "<email subject line>",
    "body": "<full email body — professional, concise, references city market data and company name. End with exactly this sign-off, do not invent a name or email:\n\nBest,\n[Your Name]\nSales Development Representative, EliseAI\n[your.email@eliseai.com]>"
  }
}

Priority mapping: score >= 70 → Hot, score 40-69 → Warm, score < 40 → Cold.

Insights should be specific and useful — e.g. "Atlanta has a 54% renter-occupied rate, indicating
strong leasing volume that EliseAI can help automate" rather than generic observations.
If red_flag is true, make the first insight a clear warning for the rep, e.g.
"⚠ Address not found in RentCast — verify this is a real rental property before outreach."

The outreach email should be 3-4 short paragraphs. Reference the city's rental market stats
naturally. Do not invent facts not present in the provided data.
""".strip()


def _build_lead_context(lead: dict) -> str:
    enrichment = lead.get("enrichment", {})
    census = enrichment.get("census", {})
    ws = enrichment.get("walkscore", {})
    rc = enrichment.get("rentcast", {})
    email_domain = enrichment.get("email_domain", "N/A")

    if not rc:
        rc_status = "Not checked (no API key)"
    elif not rc.get("found") or not rc.get("property_type"):
        rc_status = "NOT FOUND or no property type returned — address may not be a real rental property"
    else:
        rc_status = f"Found — Property Type: {rc['property_type']}"

    lines = [
        "## Lead Information",
        f"Name:         {lead.get('name', 'N/A')}",
        f"Email:        {lead.get('email', 'N/A')}",
        f"Email Domain: {email_domain}",
        f"Company:      {lead.get('company', 'N/A')}",
        f"Address:      {lead.get('address', 'N/A')}",
        f"City:         {lead.get('city', 'N/A')}",
        f"State:        {lead.get('state', 'N/A')}",
        "",
        "## City Demographics (U.S. Census ACS 5-Year Estimates)",
        f"Population:              {census.get('population', 'N/A')}",
        f"Median Household Income: {census.get('median_household_income', 'N/A')}",
        f"Renter-Occupied %:       {census.get('renter_occupied_pct', 'N/A')}",
        "",
        "## Property Location (WalkScore)",
        f"Walk Score:    {ws.get('walk_score', 'N/A')} — {ws.get('walk_description', 'N/A')}",
        f"Transit Score: {ws.get('transit_score', 'N/A')} — {ws.get('transit_description', 'N/A')}",
        f"Bike Score:    {ws.get('bike_score', 'N/A')} — {ws.get('bike_description', 'N/A')}",
        "",
        "## Address Validation (RentCast)",
        f"Status: {rc_status}",
    ]
    return "\n".join(lines)


def score_lead(lead: dict) -> dict:
    """
    Call Claude to score a lead and return a structured result.
    On API error, returns a fallback dict with score=None and an error message.
    """
    client = _get_client()
    context = _build_lead_context(lead)

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": context}],
        )
        raw = message.content[0].text.strip()
        scored = json.loads(raw)
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse LLM response as JSON: {e}", "score": None}
    except anthropic.APIError as e:
        return {"error": f"Anthropic API error: {e}", "score": None}

    return scored
