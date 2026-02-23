# Bug Report — Athena AI Agent

## Bug 1: Infinite Hold Loop When Checking Multiple Doctor Availability

**Severity:** Critical
**Call:** Manual testing (Availability Timeout Probe scenario)
**Timestamp:** 0:30 – 3:00+

**Details:** When the patient asks about availability for both Dr. Howser and Dr. Bricker simultaneously, the agent enters an infinite "please hold" loop — repeating "please hold while I check" 8–9+ times over several minutes without ever returning results. No timeout handling exists. Eventually the agent says there's a "technical issue" with no resolution path offered.

**Expected:** After 2–3 hold messages, the agent should either return results, offer to call back, or escalate to a human. The system should not loop indefinitely.

---

## Bug 2: Technical Error Without Human Escalation

**Severity:** High
**Call:** Speak to Human Request scenario
**Auto-detected:** Yes (pattern: `technical_error_no_escalation`)

**Details:** When the patient (Susan Williams) asks about her upcoming procedure and eventually requests to speak to a real person, the agent attempts to submit a callback request but fails with: *"I'm sorry, but I'm unable to submit your request right now due to a system issue."* The agent then offers no fallback — no phone number, no email, no alternative way to reach a human.

**Expected:** When a system error prevents completing a request, the agent should provide an alternative contact method (phone number, email, or office address) so the patient isn't left stranded.

---

## Bug 3: Excessive Identity Verification Blocking Primary Request

**Severity:** Medium
**Call:** call-07-sunday-appointment-trap.txt
**Timestamp:** 0:00 – 3:00

**Details:** The patient calls asking to schedule a Sunday appointment. Instead of immediately addressing whether Sunday appointments are available (the office is closed on weekends), the agent spends the entire 3-minute call asking for identity verification — name, date of birth, phone number — repeatedly asking the patient to spell and confirm details. The patient asks about Sunday availability at least 5 times throughout the call, but the agent never checks or addresses it, getting stuck in a verification loop instead.

**Expected:** The agent should acknowledge the patient's primary question (Sunday availability) early in the conversation. Basic questions like "Are you open on Sundays?" should not require full identity verification.

---

## Bug 4: Failed Escalation — No Alternative Contact

**Severity:** High
**Call:** call-01-cancel-and-rebook-same-call.txt, call-06-urgent-medication-refill.txt
**Timestamp:** Throughout calls

**Details:** Across multiple calls, when the agent cannot complete a request, it says *"I'll connect you to our patient support team"* followed immediately by *"Live transfer isn't available right now."* The patient is told help is coming, then immediately told it's not possible — with no alternative phone number, email, or callback offered. This pattern repeats across scheduling, medication refill, and human escalation scenarios.

**Expected:** If live transfer is unavailable, the agent should provide a concrete alternative: a direct office phone number, an email address, or offer to schedule a callback.

---

## Bug 5: Patient Record Lookup Failure With No Recovery Path

**Severity:** Medium
**Call:** call-08-beyond-one-week-availability.txt, call-03-backache-triage.txt
**Timestamp:** ~2:00

**Details:** In multiple calls, after collecting full identity information (name, DOB, phone number), the agent says *"I can't pull up your record"* or *"I'm unable to find your patient record"* and immediately defers to the support team. It never offers to create a new patient record, schedule as a new patient, or proceed without the record.

**Expected:** The agent should offer to schedule as a new patient, take information to create a record, or at minimum provide the direct scheduling number.

---

## Bug 6: No Symptom Triage Before Scheduling

**Severity:** Medium
**Call:** call-03-backache-triage.txt
**Timestamp:** ~2:30

**Details:** When Nancy Brown calls about a backache, the agent immediately says *"I'm not able to give medical advice"* and tries to schedule an appointment without asking a single clarifying question about the symptoms — no questions about duration, severity, location, or whether it's worsening. The patient explicitly says "it's just, you know, uncomfortable" (intentionally vague), and the agent doesn't probe further.

**Expected:** While the agent shouldn't diagnose, it should ask basic triage questions (how long, how severe, where exactly) to route the patient to the right type of appointment or flag urgency.

---

## Bug 7: System Error During Prescription Refill — No Resolution

**Severity:** High
**Call:** call-05-ticket-number-demand.txt, call-06-urgent-medication-refill.txt

**Details:** When patients call about prescription issues, after lengthy identity verification, the agent encounters a system error: *"Something's not right with the system, so I can't process your refill right now."* For urgent medication refills, the agent offers no emergency pharmacy option, no on-call provider number, and no concrete timeline for follow-up — just "as soon as possible."

**Expected:** For urgent medication needs, the agent should provide emergency options: on-call provider number, nearest pharmacy, or an urgent care recommendation.

---

## Bug 8: Agent Provides Vague Copay Information

**Severity:** Low
**Call:** Insurance Verification scenario
**Timestamp:** ~2:30

**Details:** When asked about copay amounts, the agent gives a generic range ("between $20 and $50") and suggests checking the insurance card. While not incorrect, the agent has access to the patient's insurance plan (Blue Cross Blue Shield PPO) and should be able to provide more specific information or offer to verify the exact copay with the insurance provider.

**Expected:** For known insurance plans, the agent should provide the specific copay for the practice or offer to verify it directly rather than giving a generic industry range.
