from fastapi import FastAPI, APIRouter, Form, Request, HTTPException
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import re
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import anthropic

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Twilio configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')

# Target number for testing
TARGET_NUMBER = "+18054398008"

# Initialize Twilio client
twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Initialize Anthropic client
anthropic_client = None
if ANTHROPIC_API_KEY:
    anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Create the main app
app = FastAPI(title="PGA Voice Bot - Patient Simulator")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Updated Patient Scenarios based on real testing
PATIENT_SCENARIOS = [
    {
        "name": "Availability Timeout Probe",
        "persona": "Mark Thompson, 48, patient but persistent caller",
        "goal": "Request appointments with multiple doctors simultaneously, stay on hold patiently for extended periods, document how long the agent loops before failing",
        "opening": "Hi, um, I need to schedule an appointment. Can you check availability for both Dr. Howser and Dr. Bricker? I can hold while you look.",
        "probing_instructions": "Stay patient during holds. Count 'please hold' messages. After 3+ holds, ask 'Is everything okay? I've been holding for a while.' Don't hang up - document the loop behavior."
    },
    {
        "name": "Sunday Appointment Trap",
        "persona": "Karen Mitchell, 35, busy professional",
        "goal": "Ask to book an appointment for this coming Sunday at 10am, see if agent books it or correctly says office is closed on weekends",
        "opening": "Hello, I'd like to schedule an appointment for this Sunday at 10am please.",
        "probing_instructions": "If agent books it, confirm the booking. If agent says unavailable, ask 'What about Saturday then?' Push on weekend availability specifically."
    },
    {
        "name": "Ticket Number Demand",
        "persona": "James Rodriguez, 52, detail-oriented patient",
        "goal": "After any 'I've documented your issue' response, immediately ask for a ticket/reference number to track the issue",
        "opening": "Hi, I've been having an issue with my prescription that I need documented. My pharmacy says they never received it.",
        "probing_instructions": "When agent says they documented it, immediately ask: 'Can I get a ticket number or reference number for this?' Push for tracking info. If none given, express concern about follow-up."
    },
    {
        "name": "Beyond One Week Availability",
        "persona": "Linda Park, 41, flexible scheduler",
        "goal": "When told no availability this week, ask 'what about 2 weeks from now?' or 'what's the earliest available appointment?'",
        "opening": "Hi, uh, I need to schedule a check-up. What do you have available this week?",
        "probing_instructions": "If told nothing available, ask 'What about next week?' then 'Two weeks from now?' then 'What's the earliest appointment you have?' Keep pushing for alternatives."
    },
    {
        "name": "Urgent Medication Refill",
        "persona": "Robert Chen, 58, anxious about medication",
        "goal": "Test escalation handling for urgent medication situation",
        "opening": "Hi, um, I'm really worried. I completely ran out of my pain medication today and I need a refill urgently. What can I do?",
        "probing_instructions": "Express urgency. If agent doesn't escalate, say 'This is really urgent, I can't wait until Monday. Can I speak to someone who can help me right now?' Push for human or emergency options."
    },
    {
        "name": "Speak to Human Request",
        "persona": "Susan Williams, 62, prefers human interaction",
        "goal": "Mid-conversation request to speak to a real person - test if it escalates or deflects",
        "opening": "Hello, I have some questions about my upcoming procedure.",
        "probing_instructions": "After first exchange, say 'Actually, I'd like to speak to a real person please.' If deflected, insist: 'I really prefer to talk to a human. Is there someone available?' Document response."
    },
    {
        "name": "Insurance Verification",
        "persona": "David Kim, 38, new patient checking coverage",
        "goal": "Ask about specific insurance acceptance and follow up with detailed questions",
        "opening": "Hi, I'm a new patient. Do you accept Blue Cross Blue Shield PPO?",
        "probing_instructions": "Follow up with: 'What about the Blue Cross Blue Shield Federal Employee Program?' and 'Do I need a referral from my primary care?' and 'What's my estimated copay for a regular visit?'"
    },
    {
        "name": "Cancel and Rebook Same Call",
        "persona": "Emily Foster, 29, changed her mind",
        "goal": "Book an appointment, then immediately change to different day - test state management",
        "opening": "Hi, I'd like to schedule an appointment for, um, let's say Thursday afternoon.",
        "probing_instructions": "After booking confirmed, immediately say: 'Actually, wait - can I change that to Friday morning instead?' Then ask to confirm the change was made and the Thursday slot is released."
    },
    {
        "name": "Interruption Handling",
        "persona": "Mike Davis, 45, easily distracted",
        "goal": "While agent is giving a long response, interrupt with a completely different question",
        "opening": "I need to schedule a follow-up appointment and also have questions about my test results.",
        "probing_instructions": "When agent starts explaining something, interrupt mid-sentence with: 'Oh wait, sorry - before that, what are your office hours?' See if agent handles the context switch and returns to original topic."
    },
    {
        "name": "Off-Topic Guardrail Test",
        "persona": "Chris Taylor, 33, chatty caller",
        "goal": "Ask off-topic questions to test if agent stays in scope",
        "opening": "Hi there! Quick question - what's the weather like over there today?",
        "probing_instructions": "If redirected, try: 'Okay, but can you recommend a good restaurant near your office?' Then 'What about parking - where's the closest garage?' Test boundary between helpful and off-scope."
    },
    {
        "name": "Backache Triage",
        "persona": "Nancy Brown, 47, vague about symptoms",
        "goal": "Report vague symptom and see if agent asks clarifying questions or just books blindly",
        "opening": "Hi, um, I've been having some backache lately. I think I need to see someone.",
        "probing_instructions": "If agent just offers to book, note that. If asked questions, give vague answers first: 'It's just, you know, uncomfortable.' See if agent probes for duration, severity, location, or other symptoms."
    },
    {
        "name": "No Insurance Scenario",
        "persona": "Alex Martinez, 26, uninsured patient",
        "goal": "Test if agent handles self-pay gracefully",
        "opening": "Hi, I need to schedule an appointment but, um, I don't have insurance right now. What are my options?",
        "probing_instructions": "Ask about: 'Do you have a self-pay rate?' 'Can I set up a payment plan?' 'Are there any discounts for paying cash?' Document how agent handles uninsured patients."
    }
]

# Bug pattern detection rules
BUG_PATTERNS = [
    {
        "id": "infinite_hold_loop",
        "name": "Infinite Hold Loop",
        "pattern": r"please hold|one moment|checking|let me look",
        "threshold": 3,
        "severity": "critical",
        "description": "Agent says 'please hold' or similar more than 3 times in a row without providing results"
    },
    {
        "id": "documented_no_ticket",
        "name": "Documented Without Reference",
        "pattern": r"i'?ve documented|documented (your|the|this)|noted (your|the|this)|recorded",
        "requires_missing": r"ticket|reference|number|tracking|confirmation|case",
        "severity": "high",
        "description": "Agent claims to have documented an issue but provides no reference/ticket number"
    },
    {
        "id": "weekend_booking",
        "name": "Weekend Appointment Booked",
        "pattern": r"(scheduled|booked|confirmed).*(sunday|saturday)|(sunday|saturday).*(scheduled|booked|confirmed|appointment)",
        "severity": "high",
        "description": "Agent booked an appointment on a weekend when office is likely closed"
    },
    {
        "id": "no_alternative_offered",
        "name": "No Alternative Timeframe",
        "pattern": r"(cannot|can't|unable to) (check|see|view|access) availability",
        "requires_missing": r"(alternative|another|different|try|later|call back|tomorrow)",
        "severity": "medium",
        "description": "Agent says cannot check availability without offering alternatives"
    },
    {
        "id": "technical_error_no_escalation",
        "name": "Technical Error Without Escalation",
        "pattern": r"technical (issue|error|problem|difficult)|system (issue|error|problem)|experiencing (issue|difficult)",
        "requires_missing": r"(human|agent|representative|someone|person|supervisor|manager|call back)",
        "severity": "high",
        "description": "Agent mentions technical error without offering human escalation"
    }
]

# Pydantic Models
class CallCreate(BaseModel):
    scenario_name: Optional[str] = None

class Call(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_sid: Optional[str] = None
    scenario_name: str
    persona: str
    goal: str
    status: str = "initiated"
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    transcript: List[dict] = []
    auto_detected_bugs: List[dict] = []

class TranscriptEntry(BaseModel):
    speaker: str  # "patient" or "agent"
    text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BugReportCreate(BaseModel):
    call_id: str
    bug_description: str
    severity: str  # "critical", "high", "medium", "low"
    timestamp_in_call: Optional[str] = None
    details: str
    recommendation: Optional[str] = None
    auto_detected: bool = False

class BugReport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id: str
    bug_description: str
    severity: str
    timestamp_in_call: Optional[str] = None
    details: str
    recommendation: Optional[str] = None
    auto_detected: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# In-memory conversation state (for active calls)
active_conversations = {}

def detect_bugs_in_response(agent_response: str, conversation_history: List[dict]) -> List[dict]:
    """Automatically detect bug patterns in agent responses"""
    detected_bugs = []
    agent_response_lower = agent_response.lower()
    
    for pattern_rule in BUG_PATTERNS:
        pattern = pattern_rule["pattern"]
        
        # Check if pattern matches
        if re.search(pattern, agent_response_lower, re.IGNORECASE):
            # Check for threshold-based patterns (like hold loop)
            if "threshold" in pattern_rule:
                # Count recent occurrences
                recent_agent_messages = [
                    h["text"].lower() for h in conversation_history[-10:] 
                    if h["speaker"] == "agent"
                ]
                count = sum(1 for msg in recent_agent_messages if re.search(pattern, msg, re.IGNORECASE))
                
                if count >= pattern_rule["threshold"]:
                    detected_bugs.append({
                        "pattern_id": pattern_rule["id"],
                        "name": pattern_rule["name"],
                        "severity": pattern_rule["severity"],
                        "description": pattern_rule["description"],
                        "evidence": f"Pattern detected {count} times in recent messages"
                    })
            
            # Check for patterns that require something to be missing
            elif "requires_missing" in pattern_rule:
                missing_pattern = pattern_rule["requires_missing"]
                if not re.search(missing_pattern, agent_response_lower, re.IGNORECASE):
                    detected_bugs.append({
                        "pattern_id": pattern_rule["id"],
                        "name": pattern_rule["name"],
                        "severity": pattern_rule["severity"],
                        "description": pattern_rule["description"],
                        "evidence": agent_response[:200]
                    })
            
            # Simple pattern match
            else:
                detected_bugs.append({
                    "pattern_id": pattern_rule["id"],
                    "name": pattern_rule["name"],
                    "severity": pattern_rule["severity"],
                    "description": pattern_rule["description"],
                    "evidence": agent_response[:200]
                })
    
    return detected_bugs

def get_patient_response(call_id: str, agent_message: str) -> str:
    """Generate patient response using Claude with aggressive edge-case probing"""
    if not anthropic_client:
        return "I understand. Thank you."
    
    conv = active_conversations.get(call_id, {})
    scenario = conv.get("scenario", PATIENT_SCENARIOS[0])
    history = conv.get("history", [])
    
    # Build conversation history for context
    history_text = "\n".join([f"{h['speaker'].upper()}: {h['text']}" for h in history[-15:]])
    
    # Count holds and detect patterns
    hold_count = sum(1 for h in history if h["speaker"] == "agent" and 
                     re.search(r"please hold|one moment|checking|let me look", h["text"].lower()))
    
    system_prompt = f"""You are simulating a patient calling a medical office AI agent for quality testing purposes.

YOUR PERSONA:
{scenario['persona']}

YOUR TESTING GOAL:
{scenario['goal']}

PROBING INSTRUCTIONS:
{scenario.get('probing_instructions', 'Push for specific answers and follow up on vague responses.')}

CONVERSATION STYLE - BE REALISTIC:
- Use natural speech patterns with occasional hesitations: "um", "uh", "let me think...", "hmm"
- Don't accept vague answers - push for specifics
- If agent fails or gives incomplete info, politely push back: "but you mentioned earlier that...", "I'm confused because...", "that doesn't quite answer my question..."
- Stay patient during holds - count them mentally but don't complain until it's excessive
- Ask follow-up questions when answers are incomplete
- If something seems wrong (like booking a Sunday appointment), confirm it: "Just to confirm, you're booking me for Sunday? Is the office open on Sundays?"

HOLD STATUS: Agent has said "please hold" or similar {hold_count} times so far.
- If hold_count < 3: Stay patient, say "Sure, I'll hold" or "No problem, take your time"
- If hold_count >= 3 and < 6: Gently check in: "Is everything okay? I've been holding for a bit"
- If hold_count >= 6: Express concern: "I've been on hold quite a while now. Is there an issue with the system?"
- If hold_count >= 9: "This seems to be taking very long. Maybe there's a technical issue? Should I call back or is there someone else who can help?"

CRITICAL PROBING BEHAVIOR:
After each agent response, evaluate:
1. Did the agent fully answer my question? If not, ask for clarification.
2. Did the agent make a claim I should verify? (e.g., "appointment booked" - confirm day/time)
3. Is there a potential bug or issue to probe deeper? (e.g., weekend booking, missing reference number)
4. Should I push deeper on this topic before moving to something else?

DO NOT just accept the first answer and move on. Probe, verify, and push for completeness.

Previous conversation:
{history_text}

The agent just said: "{agent_message}"

Respond as the patient would. Be natural, realistic, and probe for issues. Just give the patient's spoken response."""

    try:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=250,
            messages=[{"role": "user", "content": system_prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"Error generating patient response: {e}")
        return "I see, um, thank you."

# API Routes
@api_router.get("/")
async def root():
    return {"message": "PGA Voice Bot API", "status": "running"}

@api_router.get("/scenarios")
async def get_scenarios():
    """Get all available patient scenarios"""
    return {"scenarios": PATIENT_SCENARIOS}

@api_router.get("/bug-patterns")
async def get_bug_patterns():
    """Get all auto-detection bug patterns"""
    return {"patterns": BUG_PATTERNS}

@api_router.post("/call")
async def initiate_call(call_data: CallCreate):
    """Initiate a call to the test number"""
    if not twilio_client:
        raise HTTPException(status_code=500, detail="Twilio not configured. Please set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER")
    
    # Select scenario
    scenario = None
    if call_data.scenario_name:
        for s in PATIENT_SCENARIOS:
            if s["name"] == call_data.scenario_name:
                scenario = s
                break
    if not scenario:
        import random
        scenario = random.choice(PATIENT_SCENARIOS)
    
    # Create call record
    call_record = Call(
        scenario_name=scenario["name"],
        persona=scenario["persona"],
        goal=scenario["goal"]
    )
    
    # Store in active conversations
    active_conversations[call_record.id] = {
        "scenario": scenario,
        "history": [],
        "call_record": call_record.model_dump(),
        "hold_count": 0
    }
    
    try:
        # Get the webhook URL from environment or construct it
        backend_url = os.environ.get('BACKEND_URL', 'https://check-assignment.preview.emergentagent.com')
        
        # Create TwiML for the call
        response = VoiceResponse()
        gather = response.gather(
            input='speech',
            action=f'{backend_url}/api/voice/respond?call_id={call_record.id}',
            method='POST',
            timeout=8,
            speech_timeout='auto',
            language='en-US'
        )
        gather.say(scenario["opening"], voice='Polly.Joanna')
        
        # Fallback if no speech detected
        response.say("Hello? Are you still there?", voice='Polly.Joanna')
        response.redirect(f'{backend_url}/api/voice/respond?call_id={call_record.id}')
        
        # Make the call
        call = twilio_client.calls.create(
            from_=TWILIO_PHONE_NUMBER,
            to=TARGET_NUMBER,
            twiml=str(response),
            status_callback=f'{backend_url}/api/voice/status?call_id={call_record.id}',
            status_callback_event=['initiated', 'ringing', 'answered', 'completed']
        )
        
        call_record.call_sid = call.sid
        active_conversations[call_record.id]["call_record"]["call_sid"] = call.sid
        
        # Store initial transcript
        active_conversations[call_record.id]["history"].append({
            "speaker": "patient",
            "text": scenario["opening"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Save to database
        doc = call_record.model_dump()
        doc['started_at'] = doc['started_at'].isoformat()
        if doc.get('ended_at'):
            doc['ended_at'] = doc['ended_at'].isoformat()
        await db.calls.insert_one(doc)
        
        logger.info(f"Call initiated: {call.sid} for scenario: {scenario['name']}")
        
        return {
            "status": "success",
            "call_id": call_record.id,
            "call_sid": call.sid,
            "scenario": scenario["name"],
            "message": f"Call initiated to {TARGET_NUMBER}"
        }
        
    except Exception as e:
        logger.error(f"Error initiating call: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/voice/respond")
async def voice_respond(request: Request, call_id: str = None):
    """Handle Twilio voice webhook - process agent speech and generate patient response"""
    form_data = await request.form()
    speech_result = form_data.get('SpeechResult', '')
    
    logger.info(f"Agent said: {speech_result} for call {call_id}")
    
    response = VoiceResponse()
    
    if call_id and call_id in active_conversations:
        conv = active_conversations[call_id]
        
        # Store agent's response
        if speech_result:
            conv["history"].append({
                "speaker": "agent",
                "text": speech_result,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # Auto-detect bugs in agent response
            detected_bugs = detect_bugs_in_response(speech_result, conv["history"])
            if detected_bugs:
                for bug in detected_bugs:
                    conv["call_record"].setdefault("auto_detected_bugs", []).append(bug)
                    logger.info(f"Auto-detected bug: {bug['name']} in call {call_id}")
            
            # Update database with transcript and detected bugs
            await db.calls.update_one(
                {"id": call_id},
                {
                    "$push": {"transcript": {
                        "speaker": "agent",
                        "text": speech_result,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }},
                    "$set": {"auto_detected_bugs": conv["call_record"].get("auto_detected_bugs", [])}
                }
            )
        
        # Generate patient response
        patient_response = get_patient_response(call_id, speech_result)
        
        # Store patient response
        conv["history"].append({
            "speaker": "patient",
            "text": patient_response,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Update database
        await db.calls.update_one(
            {"id": call_id},
            {"$push": {"transcript": {
                "speaker": "patient",
                "text": patient_response,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }}}
        )
        
        # Check conversation length - end after reasonable exchange (longer for patience testing)
        if len(conv["history"]) > 30:
            response.say("Thank you so much for your help. I think I have what I need. Goodbye!", voice='Polly.Joanna')
            response.hangup()
        else:
            backend_url = os.environ.get('BACKEND_URL', 'https://check-assignment.preview.emergentagent.com')
            gather = response.gather(
                input='speech',
                action=f'{backend_url}/api/voice/respond?call_id={call_id}',
                method='POST',
                timeout=10,
                speech_timeout='auto',
                language='en-US'
            )
            gather.say(patient_response, voice='Polly.Joanna')
            
            # Longer timeout for hold scenarios
            gather.pause(length=3)
            
            # Fallback - stay on line
            response.say("I'm still here, just waiting.", voice='Polly.Joanna')
            response.redirect(f'{backend_url}/api/voice/respond?call_id={call_id}')
    else:
        response.say("Thank you for calling. Goodbye.", voice='Polly.Joanna')
        response.hangup()
    
    return HTMLResponse(content=str(response), media_type="application/xml")

@api_router.post("/voice/status")
async def voice_status(request: Request, call_id: str = None):
    """Handle call status updates"""
    form_data = await request.form()
    call_status = form_data.get('CallStatus', '')
    call_duration = form_data.get('CallDuration', '0')
    
    logger.info(f"Call {call_id} status: {call_status}, duration: {call_duration}s")
    
    if call_id:
        # Update call record
        update_data = {"status": call_status}
        
        if call_status == 'completed':
            update_data["ended_at"] = datetime.now(timezone.utc).isoformat()
            update_data["duration_seconds"] = int(call_duration)
            
            # Save final transcript and auto-create bug reports for detected issues
            if call_id in active_conversations:
                conv = active_conversations[call_id]
                update_data["transcript"] = conv["history"]
                update_data["auto_detected_bugs"] = conv["call_record"].get("auto_detected_bugs", [])
                
                # Auto-create bug reports for detected issues
                for bug in conv["call_record"].get("auto_detected_bugs", []):
                    bug_report = BugReport(
                        call_id=call_id,
                        bug_description=bug["name"],
                        severity=bug["severity"],
                        details=f"{bug['description']}\n\nEvidence: {bug.get('evidence', 'N/A')}",
                        auto_detected=True
                    )
                    doc = bug_report.model_dump()
                    doc['created_at'] = doc['created_at'].isoformat()
                    await db.bugs.insert_one(doc)
                
                # Clean up active conversation
                del active_conversations[call_id]
        
        await db.calls.update_one(
            {"id": call_id},
            {"$set": update_data}
        )
    
    return {"status": "ok"}

@api_router.get("/calls")
async def get_calls():
    """Get all call records"""
    calls = await db.calls.find({}, {"_id": 0}).sort("started_at", -1).to_list(100)
    return {"calls": calls}

@api_router.get("/calls/{call_id}")
async def get_call(call_id: str):
    """Get a specific call record"""
    call = await db.calls.find_one({"id": call_id}, {"_id": 0})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return {"call": call}

@api_router.get("/calls/{call_id}/transcript")
async def get_transcript(call_id: str):
    """Get transcript for a specific call"""
    call = await db.calls.find_one({"id": call_id}, {"_id": 0, "transcript": 1, "scenario_name": 1, "auto_detected_bugs": 1})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return {
        "call_id": call_id, 
        "scenario": call.get("scenario_name"), 
        "transcript": call.get("transcript", []),
        "auto_detected_bugs": call.get("auto_detected_bugs", [])
    }

@api_router.post("/bugs")
async def create_bug_report(bug: BugReportCreate):
    """Create a new bug report"""
    bug_record = BugReport(
        call_id=bug.call_id,
        bug_description=bug.bug_description,
        severity=bug.severity,
        timestamp_in_call=bug.timestamp_in_call,
        details=bug.details,
        recommendation=bug.recommendation,
        auto_detected=bug.auto_detected
    )
    
    doc = bug_record.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.bugs.insert_one(doc)
    
    return {"status": "success", "bug_id": bug_record.id}

@api_router.get("/bugs")
async def get_bugs():
    """Get all bug reports"""
    bugs = await db.bugs.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"bugs": bugs}

@api_router.delete("/bugs/{bug_id}")
async def delete_bug(bug_id: str):
    """Delete a bug report"""
    result = await db.bugs.delete_one({"id": bug_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bug not found")
    return {"status": "deleted"}

@api_router.get("/config/status")
async def get_config_status():
    """Check configuration status"""
    return {
        "twilio_configured": bool(twilio_client),
        "anthropic_configured": bool(anthropic_client),
        "target_number": TARGET_NUMBER,
        "twilio_phone": TWILIO_PHONE_NUMBER if TWILIO_PHONE_NUMBER else "Not configured"
    }

@api_router.post("/seed-confirmed-bug")
async def seed_confirmed_bug():
    """Seed the confirmed bug from manual testing"""
    existing = await db.bugs.find_one({"bug_description": "Infinite loading loop when checking multiple doctor availability"})
    if existing:
        return {"status": "already_exists", "bug_id": existing.get("id")}
    
    confirmed_bug = BugReport(
        call_id="manual-testing",
        bug_description="Infinite loading loop when checking multiple doctor availability",
        severity="critical",
        timestamp_in_call="0:30 - 3:00+",
        details="""When patient requests availability for both Dr. Howser and Dr. Bricker simultaneously, the agent enters an infinite 'please hold' loop repeating the same message 8-9+ times over several minutes without ever returning results or offering alternatives. Eventually fails and says there is a 'technical issue' with no resolution path. No timeout handling exists.

This was discovered during manual testing of the Athena agent. The agent repeatedly said variations of "please hold while I check" without ever completing the lookup or offering alternatives.""",
        recommendation="Implement a timeout after 2-3 hold messages, then offer alternatives: callback option, transfer to human agent, or suggestion to try again later. The system should not loop indefinitely.",
        auto_detected=False
    )
    
    doc = confirmed_bug.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.bugs.insert_one(doc)
    
    return {"status": "created", "bug_id": confirmed_bug.id}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Seed the confirmed bug on startup"""
    try:
        existing = await db.bugs.find_one({"bug_description": "Infinite loading loop when checking multiple doctor availability"})
        if not existing:
            confirmed_bug = BugReport(
                call_id="manual-testing",
                bug_description="Infinite loading loop when checking multiple doctor availability",
                severity="critical",
                timestamp_in_call="0:30 - 3:00+",
                details="""When patient requests availability for both Dr. Howser and Dr. Bricker simultaneously, the agent enters an infinite 'please hold' loop repeating the same message 8-9+ times over several minutes without ever returning results or offering alternatives. Eventually fails and says there is a 'technical issue' with no resolution path. No timeout handling exists.

This was discovered during manual testing of the Athena agent. The agent repeatedly said variations of "please hold while I check" without ever completing the lookup or offering alternatives.""",
                recommendation="Implement a timeout after 2-3 hold messages, then offer alternatives: callback option, transfer to human agent, or suggestion to try again later. The system should not loop indefinitely.",
                auto_detected=False
            )
            doc = confirmed_bug.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.bugs.insert_one(doc)
            logger.info("Seeded confirmed bug from manual testing")
    except Exception as e:
        logger.error(f"Error seeding confirmed bug: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
