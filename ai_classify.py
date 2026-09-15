"""Classifies a complaint photo using Claude's vision capability.

This is intentionally narrow in scope: it suggests a waste breakdown,
whether plastic is present, and a starting severity. It never makes a legal
or enforcement determination -- a human (the ward officer) always reviews
and can override the suggestion before anything is actioned.
"""

import base64
import json
import logging

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

CLASSIFY_PROMPT = """You are helping a municipal sanitation team triage a citizen-submitted \
photo report from Hanamkonda, Telangana, India. The complaint type is "{complaint_type}".

Look at the photo and respond with ONLY a JSON object (no markdown fences, no preamble) \
with this exact shape:

{{
  "waste_types": ["plastic bottles", "food waste", "..."],
  "plastic_detected": true,
  "severity": "low" | "medium" | "high",
  "summary": "one short sentence a sanitation worker can act on"
}}

Guidance:
- "waste_types" should list what's visibly present (empty list if nothing waste-related is visible).
- "severity" reflects visible volume/spread and any hazard (e.g. blocking a drain, near a water
  source, burning) -- not a legal judgment, just a triage signal.
- If the image doesn't clearly show what the complaint describes, still return your best-effort
  read of what's visible, and keep the summary honest about the uncertainty.
- If this is a "noise" complaint with no relevant photo, return empty waste_types, false for
  plastic_detected, "medium" severity, and a summary noting no visual waste evidence was expected.
"""


def _b64_image(path: str) -> tuple[str, str]:
    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return data, "image/jpeg"


def classify_photo(photo_path: str, complaint_type: str) -> dict | None:
    """Returns a dict with waste_types, plastic_detected, severity, summary, raw_response.

    Returns None if no API key is configured or the call fails -- callers should treat
    that as "AI classification unavailable" and fall back to the officer's manual severity.
    """
    if not settings.anthropic_api_key:
        logger.info("ANTHROPIC_API_KEY not set; skipping AI classification")
        return None

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        image_b64, media_type = _b64_image(photo_path)

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": media_type, "data": image_b64},
                        },
                        {"type": "text", "text": CLASSIFY_PROMPT.format(complaint_type=complaint_type)},
                    ],
                }
            ],
        )

        text_blocks = [b.text for b in response.content if b.type == "text"]
        raw_text = "\n".join(text_blocks).strip()
        cleaned = raw_text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(cleaned)

        return {
            "waste_types": ",".join(parsed.get("waste_types", [])),
            "plastic_detected": bool(parsed.get("plastic_detected", False)),
            "suggested_severity": parsed.get("severity", "medium"),
            "summary": parsed.get("summary", ""),
            "raw_response": raw_text,
        }
    except Exception:
        logger.exception("AI classification failed")
        return None
