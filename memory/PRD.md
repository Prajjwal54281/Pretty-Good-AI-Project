# PGA Voice Bot - Product Requirements Document

## Original Problem Statement
Build a voice bot for Pretty Good AI's engineering challenge that calls +1-805-439-8008 and simulates patient conversations to test an AI medical office agent. Requires Twilio for calls, Claude for dialogue generation, MongoDB for transcripts, and a React dashboard.

## Architecture
- **Backend**: FastAPI with Twilio voice integration and Claude claude-sonnet-4-6 for patient dialogue
- **Frontend**: React dashboard with tabs for calls, transcripts, and bug reporting
- **Database**: MongoDB for storing calls, transcripts, and bug reports
- **Voice Flow**: Twilio outbound call → TwiML with Gather/Say → Claude generates patient responses

## User Personas
1. **QA Engineer**: Uses the bot to stress-test the AI agent with various scenarios
2. **Developer**: Reviews transcripts and bug reports to improve the AI agent

## Core Requirements
- [x] `/api/call` endpoint to trigger outbound calls to test number
- [x] `/api/voice/respond` webhook for Twilio voice handling
- [x] 12 patient scenarios (scheduling, refills, questions, edge cases)
- [x] Claude claude-sonnet-4-6 for realistic patient dialogue generation
- [x] MongoDB storage for calls and transcripts
- [x] Bug reporting system with severity levels
- [x] React dashboard with 3 tabs (Dashboard, Transcripts, Bugs)

## What's Been Implemented (Jan 2026)
- Complete FastAPI backend with Twilio integration
- 12 diverse patient test scenarios
- Claude-powered conversational AI for patient responses
- Full transcript recording and storage
- Bug reporting with severity tracking
- React dashboard with modern dark UI
- Configuration status display
- All API endpoints tested and working

## Environment Variables Required
- TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER
- ANTHROPIC_API_KEY
- BACKEND_URL (for webhooks)

## Next Tasks / Backlog
### P0 (Critical)
- User needs to add real Twilio/Anthropic credentials to make calls

### P1 (Important)
- Export transcripts to text files for submission
- Generate bug report summary document

### P2 (Nice to have)
- Call recording audio storage
- Automated bug detection from transcripts
- Batch call scheduling
