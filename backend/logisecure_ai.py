# backend/logisecure_ai.py
"""
AI integration for LogiSecure
"""

import os
import requests
from dotenv import load_dotenv
from typing import Dict, Any, Optional, List
from datetime import datetime
from models import FilteredIncident
from config import settings
from logger import logger

load_dotenv()

class LogiSecureAI:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("❌ GROQ_API_KEY not found!")
        
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.model = settings.LLM_MODEL
        self.confidence_threshold = settings.CONFIDENCE_THRESHOLD
    
    def analyze_incident(self, incident_data: Dict[str, Any]) -> str:
        """Analyze a supply chain incident with confidence filtering"""
        incident = FilteredIncident(**incident_data)
        
        if not incident.is_relevant(self.confidence_threshold):
            return f"⏭️ Ignored (confidence: {incident.confidence:.0%})"
        
        prompt = self._build_prompt(incident)
        return self._call_llm(prompt)
    
    def _build_prompt(self, incident: FilteredIncident) -> str:
        context_text = incident.get_ai_prompt_context()
        
        return f"""
        Analyze this logistics incident:
        Type: {incident.type}
        Location: {incident.location}
        Severity: {incident.severity}
        Description: {incident.description}
        {context_text}
        Provide impact assessment, 3 actions, recovery time, mitigation.
        """
    
    def _call_llm(self, prompt: str) -> str:
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a logistics AI expert."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": settings.LLM_MAX_TOKENS,
            "temperature": settings.LLM_TEMPERATURE
        }
        
        try:
            response = requests.post(self.url, headers=self.headers, json=data, timeout=15)
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            return f"❌ Error: {response.status_code}"
        except Exception as e:
            return f"❌ Exception: {str(e)}"
    
    def batch_analyze(self, incidents: list) -> list:
        results = []
        for incident in incidents:
            result = self.analyze_incident(incident)
            results.append({
                "incident": incident.get('type'),
                "location": incident.get('location'),
                "confidence": incident.get('confidence', 0),
                "analysis": result
            })
        return results
    
    def get_stats(self, incidents: list) -> Dict[str, Any]:
        total = len(incidents)
        filtered = sum(1 for i in incidents if i.get('confidence', 0) < self.confidence_threshold)
        return {
            "total": total,
            "filtered": filtered,
            "processed": total - filtered,
            "threshold": self.confidence_threshold,
            "filter_rate": f"{filtered/total*100:.1f}%" if total > 0 else "0%"
        }

if __name__ == "__main__":
    ai = LogiSecureAI()
    test_incident = {
        "type": "Port Strike",
        "location": "Rotterdam",
        "severity": "High",
        "description": "Dock workers strike",
        "confidence": 0.85,
        "context": {"weather": "Clear", "traffic": "Moderate"}
    }
    print("🧪 Testing AI...\n")
    print(ai.analyze_incident(test_incident))