import json
import requests


# ── Supported providers and their models ─────────────────────

PROVIDER_MODELS = {
    "gemini": [
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash-lite-001",
        "gemini-2.0-flash",
        "gemini-2.0-flash-001",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-2.5-pro",
        "gemini-pro-latest",
    ],
    "deepseek": [
        "deepseek-chat",
        "deepseek-reasoner",
    ],
    "openai": [
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4-turbo",
    ]
}

PROVIDER_URLS = {
    "gemini": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
    "deepseek": "https://api.deepseek.com/chat/completions",
    "openai": "https://api.openai.com/v1/chat/completions",
}


class AIValidator:
    def __init__(self, provider: str, api_key: str, instructions: str):
        provider = provider.lower()

        if provider not in PROVIDER_MODELS:
            raise ValueError(f"Unsupported provider: {provider}. Choose from: {list(PROVIDER_MODELS.keys())}")

        self.provider = provider
        self.api_key = api_key
        self.instructions = instructions
        self.models = PROVIDER_MODELS[provider]
        self.url = PROVIDER_URLS[provider]

        print(f"🤖 [AI] Provider: {provider}")
        print(f"🤖 [AI] Models available: {len(self.models)}")

    def validate(self, data: dict, existing_index: list) -> dict:
        print(f"\n🤖 [AI] Starting validation...")
        print(f"🤖 [AI] Existing index has {len(existing_index)} entries")

        index_text = json.dumps(existing_index) if existing_index else "No entries yet"

        user_message = f"""
Existing entries in database:
{index_text}

[DATA]
{json.dumps(data, indent=2)}
[/DATA]

Is this valid and unique data? Reply only in JSON.
"""

        # ── Try each model in fallback chain ─────────────────
        for i, model in enumerate(self.models):
            print(f"🤖 [AI] Trying model {i+1}/{len(self.models)}: {model}")

            try:
                if self.provider == "gemini":
                    result = self._call_gemini(model, user_message)
                elif self.provider == "deepseek":
                    result = self._call_deepseek(model, user_message)
                elif self.provider == "openai":
                    result = self._call_openai(model, user_message)

                if result:
                    print(f"✅ [AI] Success with model: {model}")
                    print(f"✅ [AI] Decision: allowed={result.get('allowed')}, reason={result.get('reason')}")
                    return result

            except Exception as e:
                print(f"⚠️ [AI] Model {model} failed: {e}, trying next...")
                continue

        print("🚨 [AI] ALL MODELS FAILED")
        return {"allowed": False, "reason": "All AI models failed or unavailable"}

    # ── Gemini ────────────────────────────────────────────────

    def _call_gemini(self, model: str, message: str) -> dict | None:
        url = self.url.format(model=model, key=self.api_key)

        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": f"{self.instructions}\n\n{message}"}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 200}
            },
            timeout=30
        )

        print(f"🤖 [AI] Gemini {model} status: {response.status_code}")

        if response.status_code != 200:
            print(f"⚠️ [AI] Gemini {model} failed: {response.text[:100]}")
            return None

        content = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return self._parse(content)

    # ── Deepseek ──────────────────────────────────────────────

    def _call_deepseek(self, model: str, message: str) -> dict | None:
        response = requests.post(
            self.url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": self.instructions},
                    {"role": "user", "content": message}
                ],
                "max_tokens": 200
            },
            timeout=30
        )

        print(f"🤖 [AI] Deepseek {model} status: {response.status_code}")

        if response.status_code != 200:
            print(f"⚠️ [AI] Deepseek {model} failed: {response.text[:100]}")
            return None

        content = response.json()["choices"][0]["message"]["content"]
        return self._parse(content)

    # ── OpenAI ────────────────────────────────────────────────

    def _call_openai(self, model: str, message: str) -> dict | None:
        response = requests.post(
            self.url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": self.instructions},
                    {"role": "user", "content": message}
                ],
                "max_tokens": 200
            },
            timeout=30
        )

        print(f"🤖 [AI] OpenAI {model} status: {response.status_code}")

        if response.status_code != 200:
            print(f"⚠️ [AI] OpenAI {model} failed: {response.text[:100]}")
            return None

        content = response.json()["choices"][0]["message"]["content"]
        return self._parse(content)

    # ── Parse AI response ─────────────────────────────────────

    def _parse(self, content: str) -> dict | None:
        try:
            content = content.strip().replace("```json", "").replace("```", "").strip()
            parsed = json.loads(content)
            print(f"🤖 [AI] Parsed response: {parsed}")
            return parsed
        except json.JSONDecodeError as e:
            print(f"⚠️ [AI] Could not parse response as JSON: {e}")
            return None