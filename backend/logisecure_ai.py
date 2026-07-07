"""
LogiSecure AI - Production Ready
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LogiSecureAI:
    def __init__(self):
        """Initialize the AI client with Groq API"""
        self.api_key = os.getenv("GROQ_API_KEY")
        
        if not self.api_key:
            raise ValueError("❌ GROQ_API_KEY not found in .env file!")
        
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.model = "llama-3.1-8b-instant"  # Fastest model for real-time
    
    def analyze_supply_chain(self, incident_data):
        """
        Analyze supply chain disruptions and provide recommendations
        
        Args:
            incident_data: Dict with 'type', 'location', 'severity'
        
        Returns:
            String with AI analysis
        """
        prompt = f"""
        Analyze this logistics disruption for LogiSecure AI:
        
        Incident Type: {incident_data.get('type', 'Unknown')}
        Location: {incident_data.get('location', 'Unknown')}
        Severity: {incident_data.get('severity', 'Unknown')}
        Affected Assets: {incident_data.get('assets', 'Unknown')}
        
        Please provide:
        1. Impact Assessment (low/medium/high)
        2. 3 Recommended Actions
        3. Estimated Recovery Time
        4. Risk Mitigation Strategy
        
        Keep response concise and actionable.
        """
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a logistics AI expert for LogiSecure, an on-premise supply chain copilot."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 400,
            "temperature": 0.3
        }
        
        try:
            response = requests.post(
                self.url, 
                headers=self.headers, 
                json=data,
                timeout=15
            )
            
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            else:
                return f"❌ Error: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"❌ Exception: {str(e)}"
    
    def route_optimization(self, shipments_data):
        """
        Optimize shipping routes based on disruptions
        
        Args:
            shipments_data: List of shipment dictionaries
        
        Returns:
            Optimized route recommendations
        """
        prompt = f"""
        Optimize these shipments routes:
        {shipments_data}
        
        Provide:
        1. Alternative routes for each shipment
        2. Time estimates
        3. Priority recommendations
        """
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a route optimization expert."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 300,
            "temperature": 0.2
        }
        
        response = requests.post(
            self.url, 
            headers=self.headers, 
            json=data
        )
        
        return response.json()["choices"][0]["message"]["content"]

# Test function
if __name__ == "__main__":
    print("🚀 Testing LogiSecure AI...")
    
    # Initialize AI
    ai = LogiSecureAI()
    
    # Test supply chain analysis
    result = ai.analyze_supply_chain({
        'type': 'Port Strike',
        'location': 'Rotterdam',
        'severity': 'High',
        'assets': '5 cargo ships, 10,000 containers'
    })
    
    print("\n🤖 AI Analysis:")
    print("="*50)
    print(result)
    print("="*50)
    