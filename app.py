import json
import os
from datetime import datetime
import streamlit as st

SCHEMA_PATH = "schemas/irdai_bima_bharosa.json"

def load_schema():
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def should_show(field, answers):
    rule = field.get("show_if")
    if not rule:
        return True
    return answers.get(rule["field"]) == rule["equals"]

def render_input(field, answers):
    fid, label, ftype = field["id"], field["label"], field["type"]

    if ftype == "bool":
        answers[fid] = st.checkbox(label, value=bool(answers.get(fid, False)))
    elif ftype == "text":
        # Use text_area for long complaint details
        if fid == "complaint_details":
            answers[fid] = st.text_area(label, value=answers.get(fid, ""), height=160)
        else:
            answers[fid] = st.text_input(label, value=answers.get(fid, ""))
    else:
        st.warning(f"Unsupported field type: {ftype}")

def validate(schema, answers):
    missing = []
    for f in schema["fields"]:
        if not should_show(f, answers):
            continue
        if f.get("required") and not str(answers.get(f["id"], "")).strip():
            missing.append(f["label"])
    return missing

def build_packet(schema, answers):
    lines = []
    lines.append(f"Portal: {schema['portal_name']}")
    lines.append(f"Official form URL: {schema['official_form_url']}")
    lines.append("")
    lines.append("=== Copy/Paste Complaint Details ===")
    lines.append((answers.get("complaint_details") or "").strip())
    lines.append("")
    lines.append("=== Key Details (for form filling) ===")
    for f in schema["fields"]:
        if not should_show(f, answers):
            continue
        val = answers.get(f["id"])
        lines.append(f"- {f['label']}: {val}")
    lines.append("")
    a = schema["attachments"]
    lines.append("=== Attachments Guidance ===")
    lines.append(f"- Allowed: {', '.join(a['allowed_types'])}")
    lines.append(f"- Max file size: {a['max_size_mb']} MB")
    lines.append("")
    lines.append("=== Notes ===")
    lines.append("- This tool prepares a submission-ready packet; it does not submit on your behalf (OTP/portal checks).")
    lines.append("- For demos, mask sensitive numbers (use last 4 digits).")
    return "\n".join(lines)

st.set_page_config(page_title="BFSI Grievance Companion", layout="centered")
st.title("BFSI Grievance Filing Companion (MVP)")

schema = load_schema()

if "answers" not in st.session_state:
    st.session_state.answers = {}

answers = st.session_state.answers

st.subheader("Step 1: Fill required information")
for f in schema["fields"]:
    if should_show(f, answers):
        render_input(f, answers)

missing = validate(schema, answers)

if missing:
    st.error("Missing required fields:\n- " + "\n- ".join(missing))
else:
    st.success("All required fields collected. You can generate your packet.")

if st.button("Generate Submission Packet"):
    packet = build_packet(schema, answers)
    st.subheader("Submission Packet")
    st.code(packet, language="text")

    os.makedirs("outputs", exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    with open(f"outputs/packet_{ts}.txt", "w", encoding="utf-8") as f:
        f.write(packet)

    with open(f"logs/session_{ts}.json", "w", encoding="utf-8") as f:
        json.dump({"schema": schema["portal_id"], "answers": answers}, f, indent=2)

    st.info("Saved packet to outputs/ and session log to logs/ on your computer.")
