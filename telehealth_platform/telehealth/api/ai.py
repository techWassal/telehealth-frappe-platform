import frappe
from frappe import _
from frappe.utils import now_datetime

@frappe.whitelist()
def submit_chunk(session_id, speaker, text, timestamp=None, is_final=False, confidence=1.0):
    """
    Submits a transcript chunk. Called by LiveKit agents.
    """
    if not frappe.db.exists("Telehealth Video Session", session_id):
        frappe.local.response.http_status_code = 404
        return {"error": "Not Found", "message": _("Session not found")}
        
    s_status = frappe.db.get_value("Telehealth Video Session", session_id, "status")
    if s_status in ["Ended", "Expired", "Cancelled"]:
         frappe.local.response.http_status_code = 400
         return {"error": "Invalid State", "message": _("Cannot submit chunks to a closed session")}

    chunk = frappe.get_doc({
        "doctype": "Transcript Chunk",
        "video_session": session_id,
        "speaker": speaker,
        "text": text,
        "timestamp": timestamp or now_datetime(),
        "is_final": is_final
    })
    chunk.insert(ignore_permissions=True)
    frappe.db.commit()
    
    return {"message": _("Chunk saved")}

@frappe.whitelist()
def get_transcript(session_id):
    """
    Retrieves full transcript for a session.
    """
    chunks = frappe.get_all("Transcript Chunk",
        filters={"video_session": session_id},
        fields=["speaker", "text", "timestamp", "is_final"],
        order_by="timestamp asc"
    )
    
    return chunks

@frappe.whitelist()
def get_clinical_notes(session_id):
    """
    Retrieves clinical notes for a session.
    """
    # Resolve session ID if appointment ID is passed
    if frappe.db.exists("Telehealth Video Session", {"appointment": session_id}):
         session_id = frappe.db.get_value("Telehealth Video Session", {"appointment": session_id}, "name")

    note_name = frappe.db.get_value("Clinical Note AI", {"video_session": session_id}, "name")
    if not note_name:
        frappe.local.response.http_status_code = 404
        return {"error": "Not Found", "message": _("Notes not found")}
        
    note = frappe.get_doc("Clinical Note AI", note_name)
    return {
        "session_id": note.video_session,
        "subjective": note.subjective,
        "objective": note.objective,
        "assessment": note.assessment,
        "plan": note.plan,
        "status": note.status,
        "ai_confidence": note.ai_confidence,
        "last_updated": str(note.modified)
    }

@frappe.whitelist()
def update_clinical_notes(session_id, subjective=None, objective=None, assessment=None, plan=None):
    """
    Updates draft clinical notes.
    """
    # Resolve session ID if appointment ID is passed
    if frappe.db.exists("Telehealth Video Session", {"appointment": session_id}):
         session_id = frappe.db.get_value("Telehealth Video Session", {"appointment": session_id}, "name")

    note_name = frappe.db.get_value("Clinical Note AI", {"video_session": session_id}, "name")
    if not note_name:
        # Create if doesn't exist
        note = frappe.get_doc({
            "doctype": "Clinical Note AI",
            "video_session": session_id,
            "status": "Draft"
        })
    else:
        note = frappe.get_doc("Clinical Note AI", note_name)
        
    if note.status == "Finalized":
        frappe.throw(_("Cannot update finalized notes"), frappe.PermissionError)
        
    if subjective is not None: note.subjective = subjective
    if objective is not None: note.objective = objective
    if assessment is not None: note.assessment = assessment
    if plan is not None: note.plan = plan
    
    note.save(ignore_permissions=True)
    frappe.db.commit()
    
    return get_clinical_notes(session_id)

@frappe.whitelist()
def finalize_notes(session_id):
    """
    Finalizes clinical notes.
    """
    # Resolve session ID if appointment ID is passed
    if frappe.db.exists("Telehealth Video Session", {"appointment": session_id}):
         session_id = frappe.db.get_value("Telehealth Video Session", {"appointment": session_id}, "name")

    note_name = frappe.db.get_value("Clinical Note AI", {"video_session": session_id}, "name")
    if not note_name:
        frappe.local.response.http_status_code = 404
        return {"error": "Not Found", "message": _("Notes not found")}
        
    note = frappe.get_doc("Clinical Note AI", note_name)
    note.status = "Finalized"
    note.save(ignore_permissions=True)
    frappe.db.commit()
    
    return {"message": _("Notes finalized")}

    import openai
    
    openai_api_key = frappe.conf.get("openai_api_key")
    if not openai_api_key:
         return {
            "answer": "AI service is not configured (Missing API Key).",
            "sources": []
        }
        
    client = openai.OpenAI(api_key=openai_api_key)
    
    try:
        messages = [
            {"role": "system", "content": "You are a helpful medical assistant. Provide concise, clinical answers. Do not provide medical advice or diagnosis."},
            {"role": "user", "content": query}
        ]
        
        # In a real scenario, we would inject context from context_session_id (e.g. transcript)
        if context_session_id:
            # logic to fetch transcript headers or summary could go here
            messages.insert(1, {"role": "system", "content": f"Context: Session {context_session_id}"})
            
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        
        answer = response.choices[0].message.content
        return {
            "answer": answer,
            "sources": ["AI Generated"] 
        }
    except Exception as e:
        frappe.log_error(f"OpenAI Query Error: {str(e)}", "AI Assistant")
        return {
            "answer": "I'm sorry, I cannot process your request at the moment.",
            "sources": []
        }
