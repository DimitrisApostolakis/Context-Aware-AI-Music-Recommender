from google import genai
import json
import re

from typing import *

class LLM():
    
    def __init__(self, config:dict[str, str]) -> None:
        
        self.client = genai.Client(api_key=config["GEMINI_API_KEY"])

    def _extract_json_text(self, text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned).strip()

        try:
            json.loads(cleaned)
            return cleaned
        except Exception:
            pass

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return cleaned[start : end + 1]
        return cleaned
        
    def get_response(self, prompt:str) -> Optional[Dict[str, Any]]:
        response = self.client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
        text_content = (response.text or "").strip()
        json_text = self._extract_json_text(text_content)
        
        try:
            parsed = json.loads(json_text)
            if isinstance(parsed, dict):
                return parsed
            print("Error: AI returned JSON but not an object.")
            return None
        except json.JSONDecodeError:
            print("Error: AI returned non-JSON response.")
            return None