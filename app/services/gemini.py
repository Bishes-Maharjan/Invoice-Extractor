import json
import os
import logging
from typing import Optional
from google import genai
from google.genai import types
from google.genai.errors import APIError

logger = logging.getLogger(__name__)

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

# ---------------------------------------------------------------------------
# Strict JSON-only extraction prompt
# ---------------------------------------------------------------------------
# Two layers of enforcement:
#   1. This prompt explicitly tells the model the exact output contract.
#   2. generation_config response_mime_type="application/json" forces the
#      model's sampler to only produce valid JSON tokens at the API level.
# ---------------------------------------------------------------------------
INVOICE_EXTRACTION_PROMPT = """You are a structured invoice data extraction engine.

Your ONLY job is to analyze the provided image and return a single, valid JSON object.

RULES — follow them without exception:
- Output ONLY the raw JSON object. No markdown fences, no explanations, no preamble, no trailing text.
- Do NOT wrap the JSON in ```json``` or any other formatting.
- Never add comments inside the JSON.

STEP 1 — Determine if the image is an invoice:
  An invoice is any commercial document requesting payment: invoice, bill, receipt, purchase order, proforma invoice, credit note, or similar.

STEP 2a — If it IS an invoice, return this exact shape (replace values with extracted data):
{
  "isInvoice": true,
  "invoice_number": "string or null if not found",
  "invoice_date": "YYYY-MM-DD or null if not found",
  "supplier_name": "string or null if not found",
  "items": [
    {
      "description": "string",
      "quantity": 0,
      "unit": "string or null",
      "unit_price": 0,
      "line_total": 0
    }
  ],
  "subtotal": 0,
  "vat": 0,
  "discount": 0,
  "total_amount": 0,
  "currency": "3-letter ISO currency code or null"
}

STEP 2b — If it is NOT an invoice (e.g. a photo, screenshot, logo, blank page), return ONLY:
{
  "isInvoice": false
}

FIELD RULES:
- All numeric fields (quantity, unit_price, line_total, subtotal, vat, total_amount, discount) must be numbers (not strings). Use 0 if unknown or absent.
- invoice_date must be formatted as YYYY-MM-DD if a date is present, otherwise null.
- items must be an array; use an empty array [] if no line items are found.
- currency should be an ISO 4217 code (e.g. "USD", "EUR", "NPR"). Use null if unknown.
- If a field is not found on the invoice, set it to null (for strings/dates) or 0 (for numbers)."""

def get_gemini_client(api_key: Optional[str] = None) -> genai.Client:
    """Initialize the Google GenAI client using the provided key or environment variable."""
    resolved_key = (api_key or "").strip() or os.getenv("GEMINI_API_KEY", "").strip()
    if not resolved_key:
        raise ValueError(
            "GEMINI_API_KEY is not configured. "
            "Please provide a Gemini API key in your .env file, environment variables, or through the web interface."
        )
    return genai.Client(api_key=resolved_key)


async def extract_image_content(
    image_bytes: bytes,
    mime_type: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> dict:
    """
    Calls the Gemini Flash model to extract invoice data from the uploaded image.

    The model is forced to return a strict JSON object via two mechanisms:
      1. A system prompt that explicitly contracts the output shape.
      2. response_mime_type="application/json" in GenerateContentConfig, which
         constrains the model's token sampler to valid JSON only.

    Args:
        image_bytes: Raw binary content of the image.
        mime_type:   MIME type of the image (e.g. 'image/png', 'image/jpeg').
        api_key:     Optional API key override.
        model:       Optional model name override (defaults to gemini-2.5-flash).

    Returns:
        A dict parsed from the model's JSON response.
        Always contains at minimum: {"isInvoice": bool}
    """
    client = get_gemini_client(api_key)
    target_model = model or DEFAULT_MODEL

    image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    contents = [image_part, INVOICE_EXTRACTION_PROMPT]

    # Force JSON output at the API sampler level
    generation_config = types.GenerateContentConfig(
        response_mime_type="application/json",
    )

    async def _call(mdl: str) -> dict:
        logger.info(
            f"Sending image ({len(image_bytes)} bytes, {mime_type}) to Gemini model '{mdl}'"
        )
        response = client.models.generate_content(
            model=mdl,
            contents=contents,
            config=generation_config,
        )
        raw_text = (response.text or "").strip()

        # Strip accidental markdown fences the model might still sneak in
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("No JSON object found in model response")
        raw_text = raw_text[start:end + 1]

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as parse_err:
            logger.error(f"Model returned non-JSON despite JSON mode: {raw_text[:300]}")
            raise ValueError(
                f"Model response could not be parsed as JSON: {parse_err}"
            ) from parse_err

    try:
        return await _call(target_model)

    except APIError as e:
        logger.error(f"Gemini API error with model {target_model}: {e}")
        # Fallback: retry with gemini-2.0-flash if the requested model is unavailable
        if ("404" in str(e) or "not found" in str(e).lower()) and target_model == "gemini-2.5-flash":
            fallback_model = "gemini-2.0-flash"
            logger.warning(
                f"Model '{target_model}' not available. Retrying with fallback '{fallback_model}'..."
            )
            try:
                return await _call(fallback_model)
            except Exception as fb_err:
                raise RuntimeError(
                    f"Gemini API error (fallback {fallback_model}): {fb_err}"
                ) from fb_err
        raise RuntimeError(
            f"Gemini API error: {e.message if hasattr(e, 'message') else e}"
        ) from e

    except Exception as e:
        logger.error(f"Unexpected error during Gemini extraction: {e}")
        raise

