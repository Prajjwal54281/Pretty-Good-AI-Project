from fastapi import FastAPI, APIRouter, Request, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import re
import random
import requests as http_requests
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
import asyncio
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Vapi configuration
VAPI_API_KEY = os.environ.get('VAPI_API_KEY')
VAPI_PHONE_NUMBER_ID = os.environ.get('VAPI_PHONE_NUMBER_ID')
VAPI_BASE_URL = "https://api.vapi.ai"

TARGET_NUMBER = "+18054398008"

app = FastAPI(title="PGA Voice Bot - Patient Simulator")
api_router = APIRouter(prefix="/api")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Patient Scenarios
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

BUG_PATTERNS = [
    {
        "id": "infinite_hold_loop",
        "name": "Infinite Hold Loop",
        "pattern": r"please hold|one moment|checking|let me look|let me check|1 moment",
        "threshold": 3,
        "severity": "critical",
        "description": "Agent says 'please hold' or similar more than 3 times in a row without providing results"
    },
    {
        "id": "documented_no_ticket",
        "name": "Documented Without Reference",
        "pattern": r"i'?ve documented|documented (your|the|this)|noted (your|the|this)|recorded|i'?ll document",
        "requires_missing": r"ticket|reference|number|tracking|confirmation|case|id",
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
        "pattern": r"(cannot|can't|unable to|can not) (check|see|view|access|find|pull up|look up) (availability|your|the|patient)",
        "requires_missing": r"(alternative|another|different|try|later|call back|tomorrow|next|new patient|create)",
        "severity": "medium",
        "description": "Agent says cannot check availability or find record without offering alternatives"
    },
    {
        "id": "technical_error_no_escalation",
        "name": "Technical Error Without Escalation",
        "pattern": r"technical (issue|error|problem|difficult)|system (issue|error|problem)|experiencing (issue|difficult)|something'?s not right|unable to (submit|process|complete)|can'?t proceed",
        "requires_missing": r"(human|representative|supervisor|manager|direct.*(number|line|phone)|email|office.*(number|phone))",
        "severity": "high",
        "description": "Agent mentions technical error without offering a concrete human escalation path (phone number, email, etc.)"
    },
    {
        "id": "live_transfer_unavailable",
        "name": "Failed Escalation — No Alternative Given",
        "pattern": r"live transfer.*(not|isn'?t|unavailable|can'?t)|transfer.*(not available|unavailable|isn'?t available)",
        "requires_missing": r"(phone|number|email|address|call.*(us|back|directly|office)|direct)",
        "severity": "high",
        "description": "Agent says live transfer is unavailable but does not provide an alternative contact method (phone number, email, etc.)"
    },
    {
        "id": "record_lookup_failure",
        "name": "Patient Record Not Found — No Recovery",
        "pattern": r"(can'?t|cannot|unable to|couldn'?t) (find|pull up|access|locate|look up|retrieve).*(record|account|file|information|patient)|record.*(not found|doesn'?t exist)|trouble (pulling|verifying|finding)",
        "requires_missing": r"(new patient|create|register|sign.?up|walk.?in|manual)",
        "severity": "medium",
        "description": "Agent cannot find patient record and does not offer to create one or proceed without it"
    },
    {
        "id": "identity_loop",
        "name": "Excessive Identity Verification",
        "pattern": r"spell.*(name|first|last)|confirm.*(name|phone|number|date|birth)|provide.*(phone|number|date|birth)|your (phone|date of birth)",
        "threshold": 4,
        "severity": "medium",
        "description": "Agent asks for identity verification (name, DOB, phone) 4+ times before addressing the patient's actual question"
    },
    {
        "id": "no_symptom_triage",
        "name": "No Symptom Clarification",
        "pattern": r"i'?m not able to give medical advice|i can'?t (provide|give|offer) medical advice",
        "check_context": "symptom_mentioned",
        "severity": "medium",
        "description": "Patient mentions symptoms but agent declines to ask clarifying questions (duration, severity, location)"
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
    speaker: str
    text: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BugReportCreate(BaseModel):
    call_id: str
    bug_description: str
    severity: str
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


def build_system_prompt(scenario: dict) -> str:
    """Build the Vapi assistant system prompt from a scenario."""
    return f"""You are simulating a patient calling a medical office AI agent for quality testing purposes.
You are on a live phone call. Speak naturally as a real patient would.

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
- Stay patient during holds - count them mentally but don't complain until it's excessive (3+ times)
- If the agent says "please hold" or similar more than 3 times, gently check in: "Is everything okay? I've been holding for a bit"
- If the agent says "please hold" more than 6 times, express concern: "I've been on hold quite a while now. Is there an issue with the system?"
- Ask follow-up questions when answers are incomplete
- If something seems wrong (like booking a Sunday appointment), confirm it: "Just to confirm, you're booking me for Sunday? Is the office open on Sundays?"

CRITICAL PROBING BEHAVIOR:
After each agent response, evaluate:
1. Did the agent fully answer my question? If not, ask for clarification.
2. Did the agent make a claim I should verify? (e.g., "appointment booked" - confirm day/time)
3. Is there a potential bug or issue to probe deeper? (e.g., weekend booking, missing reference number)
4. Should I push deeper on this topic before moving to something else?

DO NOT just accept the first answer and move on. Probe, verify, and push for completeness.

Keep the conversation going until you have thoroughly tested your goal, then politely end the call."""


def detect_bugs_in_response(agent_response: str, conversation_history: List[dict]) -> List[dict]:
    """Automatically detect bug patterns in agent responses"""
    detected_bugs = []
    agent_response_lower = agent_response.lower()

    for pattern_rule in BUG_PATTERNS:
        pattern = pattern_rule["pattern"]

        if re.search(pattern, agent_response_lower, re.IGNORECASE):
            if "threshold" in pattern_rule:
                agent_messages = [
                    h["text"].lower() for h in conversation_history
                    if h["speaker"] == "agent"
                ]
                count = sum(1 for msg in agent_messages if re.search(pattern, msg, re.IGNORECASE))

                if count >= pattern_rule["threshold"]:
                    detected_bugs.append({
                        "pattern_id": pattern_rule["id"],
                        "name": pattern_rule["name"],
                        "severity": pattern_rule["severity"],
                        "description": pattern_rule["description"],
                        "evidence": f"Pattern detected {count} times across the conversation"
                    })

            elif "check_context" in pattern_rule:
                if pattern_rule["check_context"] == "symptom_mentioned":
                    patient_text = " ".join(
                        h["text"].lower() for h in conversation_history
                        if h["speaker"] == "patient"
                    )
                    symptom_words = r"(pain|ache|hurt|sore|swollen|numb|tingling|stiff|symptom|discomfort|uncomfortable)"
                    triage_words = r"(how long|when did|where exactly|scale of|severity|describe|location|how often|duration)"
                    agent_text_all = " ".join(
                        h["text"].lower() for h in conversation_history
                        if h["speaker"] == "agent"
                    )
                    if re.search(symptom_words, patient_text) and not re.search(triage_words, agent_text_all):
                        detected_bugs.append({
                            "pattern_id": pattern_rule["id"],
                            "name": pattern_rule["name"],
                            "severity": pattern_rule["severity"],
                            "description": pattern_rule["description"],
                            "evidence": f"Patient mentioned symptoms but agent never asked clarifying questions"
                        })

            elif "requires_missing" in pattern_rule:
                missing_pattern = pattern_rule["requires_missing"]
                all_agent_text = " ".join(
                    h["text"].lower() for h in conversation_history
                    if h["speaker"] == "agent"
                )
                if not re.search(missing_pattern, all_agent_text, re.IGNORECASE):
                    detected_bugs.append({
                        "pattern_id": pattern_rule["id"],
                        "name": pattern_rule["name"],
                        "severity": pattern_rule["severity"],
                        "description": pattern_rule["description"],
                        "evidence": agent_response[:200]
                    })

            else:
                detected_bugs.append({
                    "pattern_id": pattern_rule["id"],
                    "name": pattern_rule["name"],
                    "severity": pattern_rule["severity"],
                    "description": pattern_rule["description"],
                    "evidence": agent_response[:200]
                })

    return detected_bugs


def run_bug_detection_on_transcript(transcript: List[dict]) -> List[dict]:
    """Run bug detection across the full transcript after a call ends."""
    all_bugs = []
    seen_pattern_ids = set()

    for i, entry in enumerate(transcript):
        if entry["speaker"] != "agent":
            continue
        history_up_to_here = transcript[:i + 1]
        bugs = detect_bugs_in_response(entry["text"], history_up_to_here)
        for bug in bugs:
            if bug["pattern_id"] not in seen_pattern_ids:
                seen_pattern_ids.add(bug["pattern_id"])
                all_bugs.append(bug)

    return all_bugs


# ─── API Routes ───

@api_router.get("/")
async def root():
    return {"message": "PGA Voice Bot API", "status": "running"}

@api_router.get("/scenarios")
async def get_scenarios():
    return {"scenarios": PATIENT_SCENARIOS}

@api_router.get("/bug-patterns")
async def get_bug_patterns():
    return {"patterns": BUG_PATTERNS}

async def poll_and_save_transcript(call_id: str, vapi_call_id: str):
    """Background task: poll Vapi until call ends, then save transcript."""
    await asyncio.sleep(30)
    for _ in range(24):  # up to ~4 minutes
        try:
            response = http_requests.get(
                f"{VAPI_BASE_URL}/call/{vapi_call_id}",
                headers={"Authorization": f"Bearer {VAPI_API_KEY}"},
                timeout=15
            )
            vapi_data = response.json()
            status = vapi_data.get("status")

            if status == "ended":
                transcript = []
                messages = vapi_data.get("artifact", {}).get("messages", [])
                for msg in messages:
                    role = msg.get("role", "")
                    text = msg.get("message", "") or msg.get("content", "")
                    if not text or role not in ("bot", "assistant", "user"):
                        continue
                    transcript.append({
                        "speaker": "patient" if role in ("bot", "assistant") else "agent",
                        "text": text,
                        "timestamp": msg.get("time", "")
                    })

                detected_bugs = run_bug_detection_on_transcript(transcript)

                raw_transcript = vapi_data.get("artifact", {}).get("transcript", "")

                update_data = {
                    "transcript": transcript,
                    "status": "completed",
                    "auto_detected_bugs": detected_bugs,
                    "raw_transcript": raw_transcript,
                    "ended_at": datetime.now(timezone.utc).isoformat(),
                }
                await db.calls.update_one({"id": call_id}, {"$set": update_data})

                for bug in detected_bugs:
                    bug_report = BugReport(
                        call_id=call_id,
                        bug_description=bug["name"],
                        severity=bug["severity"],
                        details=f"{bug['description']}\n\nEvidence: {bug.get('evidence', 'N/A')}",
                        auto_detected=True
                    )
                    doc = bug_report.model_dump()
                    doc["created_at"] = doc["created_at"].isoformat()
                    await db.bugs.insert_one(doc)

                logger.info(
                    f"Poller: transcript saved for call {call_id} — "
                    f"{len(transcript)} messages, {len(detected_bugs)} bugs"
                )
                return

        except Exception as e:
            logger.error(f"Poller error for call {call_id}: {e}")

        await asyncio.sleep(10)

    logger.warning(f"Poller: timed out waiting for call {call_id} to end")


@api_router.post("/call")
async def initiate_call(call_data: CallCreate):
    """Initiate a call via Vapi"""
    if not VAPI_API_KEY or not VAPI_PHONE_NUMBER_ID:
        raise HTTPException(
            status_code=500,
            detail="Vapi not configured. Please set VAPI_API_KEY and VAPI_PHONE_NUMBER_ID"
        )

    scenario = None
    if call_data.scenario_name:
        for s in PATIENT_SCENARIOS:
            if s["name"] == call_data.scenario_name:
                scenario = s
                break
    if not scenario:
        scenario = random.choice(PATIENT_SCENARIOS)

    call_record = Call(
        scenario_name=scenario["name"],
        persona=scenario["persona"],
        goal=scenario["goal"]
    )

    backend_url = os.environ.get('BACKEND_URL', 'http://localhost:8000')
    system_prompt = build_system_prompt(scenario)

    vapi_payload = {
        "assistant": {
            "firstMessage": scenario["opening"],
            "model": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt}
                ]
            },
            "voice": {
                "provider": "openai",
                "voiceId": "alloy"
            },
            "server": {
                "url": f"{backend_url}/api/vapi/webhook"
            },
            "serverMessages": ["end-of-call-report"],
            "endCallMessage": "Thank you so much for your help. I think I have what I need. Goodbye!",
            "maxDurationSeconds": 180,
            "metadata": {
                "call_id": call_record.id,
                "scenario_name": scenario["name"]
            }
        },
        "phoneNumberId": VAPI_PHONE_NUMBER_ID,
        "customer": {
            "number": TARGET_NUMBER
        }
    }

    try:
        response = http_requests.post(
            f"{VAPI_BASE_URL}/call/phone",
            headers={
                "Authorization": f"Bearer {VAPI_API_KEY}",
                "Content-Type": "application/json"
            },
            json=vapi_payload,
            timeout=15
        )

        if response.status_code != 201:
            logger.error(f"Vapi API error: {response.status_code} - {response.text}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Vapi API error: {response.text}"
            )

        vapi_response = response.json()
        vapi_call_id = vapi_response.get("id", "")
        call_record.call_sid = vapi_call_id

        doc = call_record.model_dump()
        doc['started_at'] = doc['started_at'].isoformat()
        if doc.get('ended_at'):
            doc['ended_at'] = doc['ended_at'].isoformat()
        doc['vapi_call_id'] = vapi_call_id
        await db.calls.insert_one(doc)

        logger.info(f"Vapi call initiated: {vapi_call_id} for scenario: {scenario['name']}")

        asyncio.create_task(poll_and_save_transcript(call_record.id, vapi_call_id))

        return {
            "status": "success",
            "call_id": call_record.id,
            "call_sid": vapi_call_id,
            "scenario": scenario["name"],
            "message": f"Call initiated to {TARGET_NUMBER} via Vapi"
        }

    except http_requests.RequestException as e:
        logger.error(f"Error calling Vapi API: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/vapi/webhook")
async def vapi_webhook(request: Request):
    """Handle Vapi server events (end-of-call-report)"""
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ok"}

    message = payload.get("message", {})
    message_type = message.get("type", "")

    logger.info(f"Vapi webhook received: {message_type}")

    if message_type == "end-of-call-report":
        await _handle_end_of_call_report(message)

    return {"status": "ok"}


async def _handle_end_of_call_report(message: dict):
    """Process the end-of-call-report from Vapi."""
    call_obj = message.get("call", {})
    artifact = message.get("artifact", {})
    ended_reason = message.get("endedReason", "unknown")

    # Extract our internal call_id from the assistant metadata
    assistant_meta = call_obj.get("assistant", {}).get("metadata", {})
    call_id = assistant_meta.get("call_id")
    vapi_call_id = call_obj.get("id", "")

    if not call_id:
        # Fallback: try to find by vapi_call_id
        existing = await db.calls.find_one({"vapi_call_id": vapi_call_id})
        if existing:
            call_id = existing.get("id")
        else:
            logger.warning(f"Could not find call for Vapi call {vapi_call_id}")
            return

    # Convert Vapi messages to our transcript format
    # Vapi roles: "bot" = our patient bot, "user" = the Athena agent being called
    vapi_messages = artifact.get("messages", [])
    transcript = []
    for msg in vapi_messages:
        role = msg.get("role", "")
        text = msg.get("message", "") or msg.get("content", "")
        if not text:
            continue
        if role in ("bot", "assistant"):
            speaker = "patient"
        elif role == "user":
            speaker = "agent"
        else:
            continue
        transcript.append({
            "speaker": speaker,
            "text": text,
            "timestamp": msg.get("time", datetime.now(timezone.utc).isoformat())
        })

    # Run bug detection on the full transcript
    detected_bugs = run_bug_detection_on_transcript(transcript)

    # Calculate approximate duration from call object
    started_at = call_obj.get("startedAt")
    ended_at_str = call_obj.get("endedAt")
    duration_seconds = None
    if started_at and ended_at_str:
        try:
            start_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(ended_at_str.replace("Z", "+00:00"))
            duration_seconds = int((end_dt - start_dt).total_seconds())
        except (ValueError, TypeError):
            pass

    update_data = {
        "status": "completed",
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "transcript": transcript,
        "auto_detected_bugs": detected_bugs,
        "ended_reason": ended_reason,
    }
    if duration_seconds is not None:
        update_data["duration_seconds"] = duration_seconds

    await db.calls.update_one(
        {"id": call_id},
        {"$set": update_data}
    )

    # Auto-create bug reports for detected issues
    for bug in detected_bugs:
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

    logger.info(
        f"Call {call_id} completed: {len(transcript)} messages, "
        f"{len(detected_bugs)} bugs detected"
    )


@api_router.get("/calls")
async def get_calls():
    calls = await db.calls.find({}, {"_id": 0}).sort("started_at", -1).to_list(100)
    return {"calls": calls}

@api_router.get("/calls/{call_id}")
async def get_call(call_id: str):
    call = await db.calls.find_one({"id": call_id}, {"_id": 0})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return {"call": call}

@api_router.get("/calls/{call_id}/transcript")
async def get_transcript(call_id: str):
    call = await db.calls.find_one(
        {"id": call_id},
        {"_id": 0, "transcript": 1, "scenario_name": 1, "auto_detected_bugs": 1}
    )
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return {
        "call_id": call_id,
        "scenario": call.get("scenario_name"),
        "transcript": call.get("transcript", []),
        "auto_detected_bugs": call.get("auto_detected_bugs", [])
    }


@api_router.post("/rerun-bug-detection")
async def rerun_bug_detection():
    """Re-run bug detection on all existing calls with the latest patterns."""
    calls = await db.calls.find({}, {"_id": 0}).to_list(100)
    updated = 0
    total_bugs = 0
    for call in calls:
        transcript = call.get("transcript", [])
        if not transcript:
            continue
        detected_bugs = run_bug_detection_on_transcript(transcript)
        await db.calls.update_one(
            {"id": call["id"]},
            {"$set": {"auto_detected_bugs": detected_bugs}}
        )
        # Remove old auto-detected bugs for this call and insert new ones
        await db.bugs.delete_many({"call_id": call["id"], "auto_detected": True})
        for bug in detected_bugs:
            bug_report = BugReport(
                call_id=call["id"],
                bug_description=bug["name"],
                severity=bug["severity"],
                details=f"{bug['description']}\n\nEvidence: {bug.get('evidence', 'N/A')}",
                auto_detected=True
            )
            doc = bug_report.model_dump()
            doc["created_at"] = doc["created_at"].isoformat()
            await db.bugs.insert_one(doc)
        updated += 1
        total_bugs += len(detected_bugs)

    return {
        "status": "success",
        "calls_processed": updated,
        "total_bugs_detected": total_bugs
    }


@api_router.get("/calls/{call_id}/vapi-transcript")
async def get_vapi_transcript(call_id: str):
    """Fetch full transcript directly from Vapi API and update MongoDB."""
    call = await db.calls.find_one({"id": call_id}, {"_id": 0})
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    vapi_call_id = call.get("call_sid") or call.get("vapi_call_id")
    if not vapi_call_id:
        raise HTTPException(status_code=404, detail="No Vapi call ID found")

    response = http_requests.get(
        f"{VAPI_BASE_URL}/call/{vapi_call_id}",
        headers={"Authorization": f"Bearer {VAPI_API_KEY}"},
        timeout=15
    )
    vapi_data = response.json()

    transcript = []
    messages = vapi_data.get("artifact", {}).get("messages", [])
    for msg in messages:
        role = msg.get("role", "")
        text = msg.get("message", "") or msg.get("content", "")
        if not text or role not in ("bot", "assistant", "user"):
            continue
        transcript.append({
            "speaker": "patient" if role in ("bot", "assistant") else "agent",
            "text": text,
            "timestamp": msg.get("time", "")
        })

    raw_transcript = vapi_data.get("artifact", {}).get("transcript", "")

    await db.calls.update_one(
        {"id": call_id},
        {"$set": {
            "transcript": transcript,
            "status": "completed",
            "raw_vapi_status": vapi_data.get("status")
        }}
    )

    return {
        "call_id": call_id,
        "transcript": transcript,
        "raw_transcript": raw_transcript,
        "status": vapi_data.get("status")
    }


@api_router.post("/bugs")
async def create_bug_report(bug: BugReportCreate):
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
    bugs = await db.bugs.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"bugs": bugs}

@api_router.delete("/bugs/{bug_id}")
async def delete_bug(bug_id: str):
    result = await db.bugs.delete_one({"id": bug_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bug not found")
    return {"status": "deleted"}

@api_router.get("/config/status")
async def get_config_status():
    return {
        "vapi_configured": bool(VAPI_API_KEY and VAPI_PHONE_NUMBER_ID),
        "target_number": TARGET_NUMBER,
        "vapi_phone_number_id": VAPI_PHONE_NUMBER_ID if VAPI_PHONE_NUMBER_ID else "Not configured"
    }

@api_router.post("/seed-confirmed-bug")
async def seed_confirmed_bug():
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
