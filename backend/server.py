from fastapi import FastAPI, APIRouter, Form, Request, HTTPException
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
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

# Patient scenarios for testing
PATIENT_SCENARIOS = [
    {
        "name": "Simple Appointment Scheduling",
        "persona": "Sarah Johnson, 34, needs to schedule a routine checkup",
        "goal": "Schedule an appointment for next week",
        "opening": "Hi, I'd like to schedule an appointment for a routine checkup please."
    },
    {
        "name": "Reschedule Appointment",
        "persona": "Mike Chen, 45, has a conflict with his existing appointment",
        "goal": "Reschedule from Tuesday to Thursday",
        "opening": "Hello, I need to reschedule my appointment that's currently set for Tuesday."
    },
    {
        "name": "Cancel Appointment",
        "persona": "Lisa Rodriguez, 28, needs to cancel due to work travel",
        "goal": "Cancel upcoming appointment",
        "opening": "Hi, I need to cancel my appointment for this Friday."
    },
    {
        "name": "Medication Refill",
        "persona": "Robert Williams, 62, needs blood pressure medication refill",
        "goal": "Request a refill for Lisinopril",
        "opening": "Hello, I'm calling to request a refill on my blood pressure medication, Lisinopril."
    },
    {
        "name": "Office Hours Question",
        "persona": "Emma Davis, 38, wants to know weekend availability",
        "goal": "Find out if office is open on weekends",
        "opening": "Hi, I was wondering if you're open on Saturdays or Sundays?"
    },
    {
        "name": "Insurance Question",
        "persona": "David Brown, 55, checking if insurance is accepted",
        "goal": "Verify if Blue Cross Blue Shield is accepted",
        "opening": "Hello, do you accept Blue Cross Blue Shield insurance?"
    },
    {
        "name": "Location Question",
        "persona": "Jennifer Martinez, 30, needs directions",
        "goal": "Get the office address and parking information",
        "opening": "Hi, I'm a new patient and I need your address and parking information."
    },
    {
        "name": "Edge Case - Sunday Appointment",
        "persona": "Tom Wilson, 42, tries to book on Sunday",
        "goal": "Try to schedule for Sunday morning",
        "opening": "Hi, can I schedule an appointment for this Sunday at 10am?"
    },
    {
        "name": "Edge Case - Interruption",
        "persona": "Nancy Lee, 50, speaks with interruptions",
        "goal": "Schedule appointment while being interrupted",
        "opening": "Hi, I need to schedule... hold on... sorry, I need to schedule an appointment."
    },
    {
        "name": "Edge Case - Unclear Request",
        "persona": "Chris Taylor, 35, vague about needs",
        "goal": "Make an unclear request to test agent clarification",
        "opening": "Hi, um, I think I might need to do something about my thing... the appointment or whatever."
    },
    {
        "name": "Urgent Appointment",
        "persona": "Amanda Green, 29, needs urgent same-day appointment",
        "goal": "Get an urgent same-day appointment for flu symptoms",
        "opening": "Hi, I'm feeling really sick and need to see a doctor today if possible."
    },
    {
        "name": "New Patient Registration",
        "persona": "Kevin White, 40, new to the practice",
        "goal": "Register as a new patient and schedule first visit",
        "opening": "Hello, I'm looking to become a new patient at your practice."
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

class TranscriptEntry(BaseModel):
    speaker: str  # "patient" or "agent"
    text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BugReportCreate(BaseModel):
    call_id: str
    bug_description: str
    severity: str  # "high", "medium", "low"
    timestamp_in_call: Optional[str] = None
    details: str

class BugReport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    call_id: str
    bug_description: str
    severity: str
    timestamp_in_call: Optional[str] = None
    details: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# In-memory conversation state (for active calls)
active_conversations = {}

def get_patient_response(call_id: str, agent_message: str) -> str:
    """Generate patient response using Claude"""
    if not anthropic_client:
        return "I understand. Thank you."
    
    conv = active_conversations.get(call_id, {})
    scenario = conv.get("scenario", PATIENT_SCENARIOS[0])
    history = conv.get("history", [])
    
    # Build conversation history for context
    history_text = "\n".join([f"{h['speaker'].upper()}: {h['text']}" for h in history[-10:]])
    
    system_prompt = f"""You are simulating a patient calling a medical office AI agent. 
Your persona: {scenario['persona']}
Your goal: {scenario['goal']}

You must stay in character as this patient. Respond naturally as a real patient would.
Keep responses concise (1-2 sentences typically).
If the agent asks for information, provide reasonable fake details that fit your persona.
If something seems wrong with the agent's response (like scheduling on a closed day), 
you can gently question it but don't be overly critical.

Previous conversation:
{history_text}

The agent just said: "{agent_message}"

Respond as the patient would. Just give the patient's response, no labels or prefixes."""

    try:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-6-20250514",
            max_tokens=200,
            messages=[{"role": "user", "content": system_prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"Error generating patient response: {e}")
        return "I see, thank you."

# API Routes
@api_router.get("/")
async def root():
    return {"message": "PGA Voice Bot API", "status": "running"}

@api_router.get("/scenarios")
async def get_scenarios():
    """Get all available patient scenarios"""
    return {"scenarios": PATIENT_SCENARIOS}

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
        "call_record": call_record.model_dump()
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
            timeout=5,
            speech_timeout='auto',
            language='en-US'
        )
        gather.say(scenario["opening"], voice='Polly.Joanna')
        
        # Fallback if no speech detected
        response.say("I'm sorry, I didn't hear anything. Goodbye.", voice='Polly.Joanna')
        response.hangup()
        
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
            
            # Update database
            await db.calls.update_one(
                {"id": call_id},
                {"$push": {"transcript": {
                    "speaker": "agent",
                    "text": speech_result,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }}}
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
        
        # Check conversation length - end after reasonable exchange
        if len(conv["history"]) > 20:
            response.say("Thank you so much for your help. Goodbye!", voice='Polly.Joanna')
            response.hangup()
        else:
            backend_url = os.environ.get('BACKEND_URL', 'https://check-assignment.preview.emergentagent.com')
            gather = response.gather(
                input='speech',
                action=f'{backend_url}/api/voice/respond?call_id={call_id}',
                method='POST',
                timeout=5,
                speech_timeout='auto',
                language='en-US'
            )
            gather.say(patient_response, voice='Polly.Joanna')
            
            # Fallback
            response.say("I'm still here. Can you hear me?", voice='Polly.Joanna')
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
            
            # Save final transcript
            if call_id in active_conversations:
                conv = active_conversations[call_id]
                update_data["transcript"] = conv["history"]
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
    call = await db.calls.find_one({"id": call_id}, {"_id": 0, "transcript": 1, "scenario_name": 1})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return {"call_id": call_id, "scenario": call.get("scenario_name"), "transcript": call.get("transcript", [])}

@api_router.post("/bugs")
async def create_bug_report(bug: BugReportCreate):
    """Create a new bug report"""
    bug_record = BugReport(
        call_id=bug.call_id,
        bug_description=bug.bug_description,
        severity=bug.severity,
        timestamp_in_call=bug.timestamp_in_call,
        details=bug.details
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

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
