"""Export call transcripts from MongoDB to text files for submission."""
import requests
import os

resp = requests.get("http://localhost:8000/api/calls")
calls = resp.json()["calls"]

os.makedirs("transcripts", exist_ok=True)

idx = 0
for c in calls:
    transcript = c.get("transcript", [])
    has_patient = any(t["speaker"] == "patient" for t in transcript)
    has_agent = any(t["speaker"] == "agent" for t in transcript)
    if len(transcript) >= 10 and has_patient and has_agent:
        idx += 1
        scenario_slug = c["scenario_name"].lower().replace(" ", "-")
        fname = f"transcripts/call-{idx:02d}-{scenario_slug}.txt"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(f"Scenario: {c['scenario_name']}\n")
            f.write(f"Persona: {c.get('persona', 'N/A')}\n")
            f.write(f"Goal: {c.get('goal', 'N/A')}\n")
            f.write(f"Status: {c.get('status', 'N/A')}\n")
            f.write(f"Started: {c.get('started_at', 'N/A')}\n")
            f.write(f"Ended: {c.get('ended_at', 'N/A')}\n")
            f.write(f"Messages: {len(transcript)}\n")
            f.write(f"Auto-detected bugs: {len(c.get('auto_detected_bugs', []))}\n")
            f.write("-" * 60 + "\n\n")
            for t in transcript:
                speaker = "PATIENT" if t["speaker"] == "patient" else "AGENT"
                f.write(f"[{speaker}]: {t['text']}\n\n")
            bugs = c.get("auto_detected_bugs", [])
            if bugs:
                f.write("-" * 60 + "\n")
                f.write("AUTO-DETECTED BUGS:\n\n")
                for b in bugs:
                    f.write(f"  [{b['severity'].upper()}] {b['name']}\n")
                    f.write(f"  {b['description']}\n")
                    f.write(f"  Evidence: {b.get('evidence', 'N/A')}\n\n")
        print(f"  Written: {fname}")

print(f"\nTotal transcript files exported: {idx}")
