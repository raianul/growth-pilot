import json
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------- Provider detection ----------

def _detect_provider() -> str:
    """Determine LLM provider from settings. Priority: explicit setting > anthropic > perplexity > ollama."""
    if settings.llm_provider:
        return settings.llm_provider.lower()
    if settings.anthropic_api_key:
        return "anthropic"
    if settings.perplexity_api_key:
        return "perplexity"
    return "ollama"

LLM_PROVIDER = _detect_provider()
logger.info("LLM provider: %s", LLM_PROVIDER)

# Init Anthropic client if needed
if LLM_PROVIDER == "anthropic":
    import anthropic
    _anthropic_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    SONNET_MODEL = "claude-sonnet-4-6-20250514"
    HAIKU_MODEL = "claude-haiku-4-5-20251001"
else:
    _anthropic_client = None
    SONNET_MODEL = HAIKU_MODEL = ""


# ---------- System prompts ----------

ANALYSIS_SYSTEM_PROMPT = """You are GrowthPilot's audit analyst. You analyze local business digital presence data and identify gaps and strengths compared to competitors.

Always respond with valid JSON matching this schema:
{
  "gaps": ["string"],
  "strengths": ["string"],
  "priority_areas": ["string"],
  "competitor_advantages": ["string"]
}

Respond ONLY with the JSON object, no markdown, no explanation."""

MISSIONS_SYSTEM_PROMPT = """You are GrowthPilot's mission planner. Given audit analysis results, generate exactly 3 actionable missions for a local business owner. Each mission should be completable in 15-30 minutes.

IMPORTANT RULES:
- If the business already has a website, do NOT suggest "create a website" or "launch a website." Instead suggest improvements like adding Schema markup, meta descriptions, blog content, or fixing specific issues.
- Each mission must be DIFFERENT — never suggest the same thing twice.
- Focus on the biggest gaps identified in the analysis.
- Be specific to the business, not generic advice.

Always respond with a valid JSON array of missions:
[{
  "title": "string",
  "description": "string (2-3 sentences, actionable and specific to this business)",
  "channel": "google_maps|website|social|youtube",
  "impact_score": 1-10,
  "difficulty": "easy|medium|hard",
  "estimated_minutes": 15-30
}]

Respond ONLY with the JSON array, no markdown, no explanation."""

CONTENT_SYSTEM_PROMPT = """You are GrowthPilot's content writer. Generate ready-to-use content for a local business. Match the brand's tone of voice. Content should be copy-paste ready.

Always respond with valid JSON:
{
  "title": "string",
  "body": "string (the actual content to post/publish)"
}

Respond ONLY with the JSON object, no markdown, no explanation."""

CONTENT_QUALITY_PROMPT = """You are analyzing a local business website. Rate the content quality.

Respond with valid JSON:
{
  "quality": "high|medium|low",
  "has_business_info": true,
  "has_contact_info": true,
  "has_product_details": true,
  "has_clear_cta": true,
  "summary": "1 sentence assessment"
}

Respond ONLY with JSON."""

REVIEW_ANALYSIS_PROMPT = """You are analyzing customer reviews for a local business. Given these reviews, provide structured insights.

Always respond with valid JSON:
{
  "summary": "2-3 sentence overall summary",
  "top_praised": ["string — things customers love, with frequency"],
  "top_complaints": ["string — common complaints, with frequency"],
  "keyword_insights": ["string — specific product/service keywords mentioned"],
  "sentiment": "positive|mixed|negative",
  "improvement_suggestions": ["string — actionable suggestions based on complaints"],
  "review_quality": "high|medium|low — whether reviews contain specific keywords vs generic praise"
}

Respond ONLY with the JSON object, no markdown, no explanation."""


# ---------- Provider call functions ----------

async def _call_ollama(system: str, user_message: str) -> str:
    """Call Ollama's chat API."""
    headers = {}
    if settings.ollama_api_key:
        headers["Authorization"] = f"Bearer {settings.ollama_api_key}"

    async with httpx.AsyncClient(base_url=settings.ollama_base_url, timeout=120.0, headers=headers) as c:
        response = await c.post(
            "/api/chat",
            json={
                "model": settings.ollama_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_message},
                ],
                "stream": False,
                "format": "json",
            },
        )
    response.raise_for_status()
    return response.json()["message"]["content"]


async def _call_anthropic(model: str, system: str, user_message: str, max_tokens: int) -> str:
    """Call Anthropic Claude API."""
    message = await _anthropic_client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return message.content[0].text


async def _call_perplexity(system: str, user_message: str, max_tokens: int = 2000) -> str:
    """Call Perplexity Sonar API (OpenAI-compatible chat completions)."""
    async with httpx.AsyncClient(timeout=120.0) as c:
        response = await c.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.perplexity_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.perplexity_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": max_tokens,
            },
        )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


async def _call_llm(system: str, user_message: str, model: str = "sonnet", max_tokens: int = 2000) -> str:
    """Route to the configured LLM provider."""
    if LLM_PROVIDER == "anthropic":
        anthropic_model = SONNET_MODEL if model == "sonnet" else HAIKU_MODEL
        return await _call_anthropic(anthropic_model, system, user_message, max_tokens)
    elif LLM_PROVIDER == "perplexity":
        return await _call_perplexity(system, user_message, max_tokens)
    else:
        return await _call_ollama(system, user_message)


# ---------- JSON parsing ----------

def _parse_json(text: str):
    """Parse JSON from LLM response, handling common formatting issues."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    parsed = json.loads(text)
    if isinstance(parsed, dict):
        for key in ("missions", "results", "items", "data"):
            if key in parsed and isinstance(parsed[key], list):
                return parsed[key]
    return parsed


# ---------- Public API ----------

async def assess_content_quality(business_name: str, content: str) -> dict:
    """Assess website content quality using AI."""
    if not content or len(content) < 100:
        return {
            "quality": "low",
            "summary": "Very little or no content found",
            "has_business_info": False,
            "has_contact_info": False,
            "has_product_details": False,
            "has_clear_cta": False,
        }

    truncated = content[:2000]
    text = await _call_llm(
        CONTENT_QUALITY_PROMPT,
        f"Assess this website content for {business_name}:\n\n{truncated}",
        model="haiku",
        max_tokens=500,
    )
    return _parse_json(text)


async def analyze_reviews(business_name: str, reviews: list[dict]) -> dict:
    """Analyze customer reviews using AI."""
    if not reviews:
        return {"summary": "No reviews to analyze", "top_praised": [], "top_complaints": [], "keyword_insights": [], "sentiment": "unknown", "improvement_suggestions": [], "review_quality": "low"}

    review_texts = []
    for r in reviews[:20]:
        rating = int(r.get('rating') or 0)
        stars = f"{'★' * rating}{'☆' * (5 - rating)}"
        text = r.get("text", "").strip()
        if text:
            review_texts.append(f"{stars} — {text}")

    if not review_texts:
        return {"summary": "Reviews have no text content", "top_praised": [], "top_complaints": [], "keyword_insights": [], "sentiment": "unknown", "improvement_suggestions": [], "review_quality": "low"}

    user_message = f"""Analyze these customer reviews for {business_name}:

{chr(10).join(review_texts)}

Identify what customers love, what they complain about, and what the business should improve."""

    text = await _call_llm(REVIEW_ANALYSIS_PROMPT, user_message, model="sonnet")
    return _parse_json(text)


async def analyze_audit_data(brand_name: str, audit_dimensions: dict, competitor_data: list[dict]) -> dict:
    if settings.dev_mode and LLM_PROVIDER == "ollama":
        from app.services.mock import mock_analysis
        return mock_analysis(brand_name)

    user_message = f"""Analyze this local business audit data:

Brand: {brand_name}
Audit dimensions: {json.dumps(audit_dimensions)}
Competitor data: {json.dumps(competitor_data)}

Identify gaps, strengths, and priority improvement areas."""

    text = await _call_llm(ANALYSIS_SYSTEM_PROMPT, user_message, model="sonnet")
    return _parse_json(text)


async def generate_missions(brand_name: str, analysis: dict, brand_voice: str, website_url: str = "") -> list[dict]:
    if settings.dev_mode and LLM_PROVIDER == "ollama":
        from app.services.mock import mock_missions
        return mock_missions(brand_name)

    website_note = f"\nWebsite: {website_url} (already exists — suggest improvements, NOT 'create a website')" if website_url else "\nNo website found."

    user_message = f"""Generate 3 missions for this business:

Brand: {brand_name}
Brand voice: {brand_voice}{website_note}
Analysis: {json.dumps(analysis)}

Prioritize missions that address the biggest gaps with the highest impact. Each mission must be different."""

    text = await _call_llm(MISSIONS_SYSTEM_PROMPT, user_message, model="sonnet")
    result = _parse_json(text)
    if isinstance(result, dict):
        for v in result.values():
            if isinstance(v, list):
                return v
        if "title" in result:
            return [result]
        logger.warning("generate_missions got unexpected dict: %s", list(result.keys()))
        return []
    return result


async def generate_content(mission_title: str, channel: str, brand_name: str, brand_voice: str, context: dict) -> dict:
    if settings.dev_mode and LLM_PROVIDER == "ollama":
        from app.services.mock import mock_content
        return mock_content(mission_title, channel, brand_name)

    user_message = f"""Generate content for this mission:

Mission: {mission_title}
Channel: {channel}
Brand: {brand_name}
Brand voice: {brand_voice}
Context: {json.dumps(context)}

Write ready-to-use content the business owner can copy and paste."""

    text = await _call_llm(CONTENT_SYSTEM_PROMPT, user_message, model="haiku", max_tokens=1500)
    return _parse_json(text)
