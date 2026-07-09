# backend/agents.py
"""
LogiSecure Agents - Complete 5-Step Architecture
Using Fireworks AI
"""

from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any
from langchain_fireworks import ChatFireworks  # ← CHANGED to Fireworks
from langchain_core.messages import HumanMessage, SystemMessage
from datetime import datetime
from config import settings
from logger import logger

class LogiSecureState(TypedDict):
    step: int
    incident_data: Dict[str, Any]
    affected_shipments: List[Dict]
    impact_analysis: str
    alternative_routes: List[Dict]
    execution_plan: Dict
    alerts: List[Dict]
    status: str
    messages: List[str]

class LogiSecureAgents:
    def __init__(self):
        logger.info("🚀 Initializing LogiSecure Agents with Fireworks AI...")
        try:
            # ← CHANGED to Fireworks
            self.llm = ChatFireworks(
                model=settings.FIREWORKS_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                max_tokens=settings.LLM_MAX_TOKENS,
                api_key=settings.FIREWORKS_API_KEY,
                base_url=settings.FIREWORKS_BASE_URL
            )
            self.workflow = self._build_workflow()
            self.app = self.workflow.compile()
            logger.info(f"✅ Agents initialized with: {settings.FIREWORKS_MODEL}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize: {str(e)}")
            raise
    
    def _monitor(self, state: LogiSecureState) -> LogiSecureState:
        logger.info("🌍 [Step 1] Monitoring global supply chain...")
        state["messages"].append("✅ Monitoring complete")
        state["step"] = 2
        return state
    
    def _detect(self, state: LogiSecureState) -> LogiSecureState:
        logger.info("⚠️ [Step 2] Detecting incidents...")
        
        incident = state.get("incident_data", {})
        confidence = incident.get('confidence', 0.5)
        
        if confidence < settings.CONFIDENCE_THRESHOLD:
            state["messages"].append(f"⏭️ Low confidence: {confidence:.0%}")
            state["step"] = 3
            return state
        
        prompt = f"""
        Analyze this incident:
        Type: {incident.get('type', 'Unknown')}
        Location: {incident.get('location', 'Unknown')}
        Severity: {incident.get('severity', 'Unknown')}
        Confidence: {confidence:.0%}
        """
        
        try:
            response = self.llm.invoke([
                SystemMessage(content="You are a logistics incident detection expert."),
                HumanMessage(content=prompt)
            ])
            state["impact_analysis"] = response.content
            state["messages"].append(f"⚠️ Detected: {response.content[:100]}...")
        except Exception as e:
            logger.error(f"Detection failed: {str(e)}")
            state["impact_analysis"] = f"Error: {str(e)}"
        
        state["step"] = 3
        return state
    
    def _correlate(self, state: LogiSecureState) -> LogiSecureState:
        logger.info("📦 [Step 3] Correlating with local assets...")
        
        affected = [
            {"id": "SHIP-001", "cargo": "Electronics", "location": "Rotterdam"},
            {"id": "SHIP-002", "cargo": "Medical Supplies", "location": "North Sea"},
            {"id": "SHIP-003", "cargo": "Auto Parts", "location": "Antwerp"}
        ]
        state["affected_shipments"] = affected
        state["messages"].append(f"📦 Found {len(affected)} affected shipments")
        state["step"] = 4
        return state
    
    def _analyze(self, state: LogiSecureState) -> LogiSecureState:
        logger.info("🧠 [Step 4] Running inference...")
        
        state["alternative_routes"] = [
            {"route": "Rotterdam → Hamburg", "time": "2 days", "priority": "High"},
            {"route": "Rotterdam → Antwerp", "time": "3 days", "priority": "Medium"},
            {"route": "Rotterdam → Amsterdam", "time": "4 days", "priority": "Low"}
        ]
        state["messages"].append("🧠 Analysis complete")
        state["step"] = 5
        return state
    
    def _execute(self, state: LogiSecureState) -> LogiSecureState:
        logger.info("⚡ [Step 5] Executing...")
        
        state["execution_plan"] = {
            "gps_updates": ["SHIP-001 → 51.92°N, 4.48°E"],
            "client_alerts": ["📧 Draft email ready"],
            "api_calls": ["📡 Updated transit operators"]
        }
        state["alerts"].append({
            "type": "success",
            "message": "Execution complete",
            "timestamp": datetime.now().isoformat()
        })
        state["status"] = "completed"
        state["messages"].append("⚡ Execution complete")
        return state
    
    def _build_workflow(self):
        workflow = StateGraph(LogiSecureState)
        workflow.add_node("monitor", self._monitor)
        workflow.add_node("detect", self._detect)
        workflow.add_node("correlate", self._correlate)
        workflow.add_node("analyze", self._analyze)
        workflow.add_node("execute", self._execute)
        workflow.set_entry_point("monitor")
        workflow.add_edge("monitor", "detect")
        workflow.add_edge("detect", "correlate")
        workflow.add_edge("correlate", "analyze")
        workflow.add_edge("analyze", "execute")
        workflow.add_edge("execute", END)
        return workflow
    
    def run(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("=" * 60)
        logger.info("🚀 STARTING 5-STEP WORKFLOW (Fireworks AI)")
        logger.info("=" * 60)
        
        initial_state = {
            "step": 1,
            "incident_data": incident_data,
            "affected_shipments": [],
            "impact_analysis": "",
            "alternative_routes": [],
            "execution_plan": {},
            "alerts": [],
            "status": "running",
            "messages": []
        }
        
        try:
            final_state = self.app.invoke(initial_state)
            logger.info("✅ WORKFLOW COMPLETE!")
            return final_state
        except Exception as e:
            logger.error(f"❌ Workflow failed: {str(e)}")
            return {**initial_state, "status": "failed"}
    
    def get_summary(self, state: Dict[str, Any]) -> str:
        summary = f"""
        📊 LOGISECURE SUMMARY
        {'='*40}
        Provider: Fireworks AI
        Model: {settings.FIREWORKS_MODEL}
        Status: {state.get('status', 'Unknown')}
        Affected: {len(state.get('affected_shipments', []))}
        Routes: {len(state.get('alternative_routes', []))}
        Alerts: {len(state.get('alerts', []))}
        """
        for msg in state.get('messages', []):
            summary += f"  • {msg}\n"
        return summary