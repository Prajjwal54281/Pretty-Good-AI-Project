# Loom Walkthrough Script (Max 5 Minutes)

Use this as your guide when recording the Loom video. They said the Loom is one of the most important deliverables — it shows how you think.

---

## 0:00–0:30 — What I Built

"I built a voice bot that automatically calls the Athena agent, simulates realistic patient conversations, and detects bugs. Instead of manually calling the agent and taking notes, the bot runs different scenarios — scheduling, insurance questions, escalation requests — records both sides of the conversation, and flags issues automatically."

---

## 0:30–1:30 — Architecture & Design Choices

Show the code briefly (server.py open in IDE).

"The system has three parts:

**Vapi AI** handles the entire voice pipeline. I send one API call with a system prompt and a phone number, and Vapi creates the outbound call, handles speech-to-text, runs the LLM conversation, and does text-to-speech. I chose Vapi because it abstracts the entire voice stack — I don't need to separately manage Twilio, a transcription service, and a TTS engine.

**FastAPI backend** orchestrates everything. It builds a scenario-specific system prompt, tells Vapi to make the call, then polls Vapi after the call ends to get the full transcript. It runs nine regex-based bug detection patterns against the transcript — things like hold loops, missing ticket numbers, weekend bookings, failed escalations, record lookup failures.

**React dashboard** displays everything — call history, two-sided transcripts, and bug reports with severity levels."

Point to the 12 scenarios in server.py:

"I wrote 12 test scenarios. Each one has a persona, a goal, and probing instructions. The bot doesn't just ask one question and hang up — it pushes back on vague answers, asks follow-ups, and confirms suspicious responses. For example, the Sunday Appointment Trap specifically asks for a Sunday appointment and if the agent books it, that's a bug."

---

## 1:30–2:30 — Live Demo

Open `localhost:3000` in browser.

"Here's the dashboard. You can see past call history, scenario selector, and the bug count."

Show existing calls:

"I've run multiple calls across different scenarios. Let me click into this Sunday Appointment Trap call..."

Click into a call with a full transcript:

"You can see both sides — the patient bot on the left and the Athena agent on the right. The bot kept asking about Sunday availability, but the agent spent the entire call stuck in identity verification — asking for name, date of birth, phone number — and never actually answered whether Sunday appointments exist."

Navigate to Bug Reports tab:

"The system auto-detected this one — Technical Error Without Escalation. The agent hit a system error and just said 'I'm unable to submit your request' without offering any alternative."

---

## 2:30–3:30 — Bugs I Found

"Let me walk through the key bugs:

**Critical — Infinite Hold Loop.** When you ask about two doctors' availability simultaneously, the agent enters a loop. It says 'please hold while I check' eight or nine times over several minutes and never returns results. No timeout, no fallback.

**High — No Human Escalation.** When the patient asks to speak to a real person, the agent says 'live transfer is not available' but doesn't offer any alternative — no callback, no direct number, nothing.

**Medium — Verification Loop Blocking Primary Request.** A simple question like 'Are you open on Sundays?' shouldn't require full identity verification. The agent got stuck asking for name and phone number and never addressed the actual question.

I documented eight bugs total in the bug report, all with severity levels and expected behavior."

---

## 3:30–4:30 — Iteration & What I'd Improve

"I iterated on a few things during development:

First, I started with PlayHT for voice but it was timing out, so I switched to OpenAI's TTS which is faster and more reliable.

I also discovered that Vapi uses 'bot' as the role name instead of 'assistant' — my initial transcripts only showed one side of the conversation. Once I found that in the raw API data, I fixed the role mapping and got full two-sided transcripts.

If I had more time, I'd add:
- Batch call scheduling to run all 12 scenarios automatically
- A scoring system that rates each call on a scale
- Audio recording storage so you can listen to the actual calls
- More sophisticated bug detection using an LLM to analyze transcripts instead of just regex"

---

## 4:30–5:00 — Closing

"The main takeaway: this tool lets you run dozens of test calls, catch bugs automatically, and build a documented record of every issue. It's reusable — change the phone number and scenarios and it works for any voice AI agent."

---

## Tips for Recording

- Share your screen with the dashboard open
- Have `server.py` open in a tab to show the scenarios and bug patterns
- If you want to trigger a live call during recording, pick "Sunday Appointment Trap" — it produces clear results
- Speak naturally, don't read word-for-word
- The script above is ~4.5 minutes if read at normal pace — you have room to breathe
