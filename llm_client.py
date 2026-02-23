from google import genai
import json

class LLM():
    
    def __init__(self, config):
        
        self.client = genai.Client(api_key=config["GEMINI_API_KEY"])
        
    def get_response(self, prompt):
        response = self.client.models.generate_content(model="gemini-3-flash-preview", contents=prompt)
        text_content = response.text.strip()
        if text_content.startswith("```json"):
            text_content = text_content.replace("```json", "").replace("```", "").strip()
        
        try:
            return json.loads(text_content)
        except json.JSONDecodeError:
            print("Error: AI returned non-JSON response")
            return None