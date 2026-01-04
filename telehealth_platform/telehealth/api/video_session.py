import frappe
from frappe import _
from frappe.utils import now_datetime
from telehealth_platform.telehealth.utils import livekit_utils

@frappe.whitelist()
def create(appointment_id):
    """
    Creates a new video session.
    """
    if not frappe.db.exists("Patient Appointment", appointment_id):
        frappe.local.response.http_status_code = 404
        return {"error": "Not Found", "message": _("Appointment not found")}

    appointment = frappe.get_doc("Patient Appointment", appointment_id)
    
    # Check if session already exists
    session_name = frappe.db.get_value("Telehealth Video Session", {"appointment": appointment_id}, "name")
    
    if not session_name:
        # Create new session record
        room_name = f"room-{appointment_id}"
        session = frappe.get_doc({
            "doctype": "Telehealth Video Session",
            "appointment": appointment_id,
            "room_name": room_name,
            "status": "Active",
            "started_at": now_datetime()
        })
        session.insert(ignore_permissions=True)
        frappe.db.commit()
        session_name = session.name
    else:
        session = frappe.get_doc("Telehealth Video Session", session_name)

    # Determine user identity and role
    user = frappe.session.user
    role = "patient"
    full_name = frappe.db.get_value("User", user, "full_name") or user
    
    # Simple role check (in reality, check against app specific roles)
    if "Doctor" in frappe.get_roles(user):
        role = "doctor"

    import json
    metadata = json.dumps({
        "role": role,
        "user_id": user,
        "full_name": full_name
    })

    token = livekit_utils.generate_token(
        room_name=session.room_name,
        identity=user,
        name=full_name,
        metadata=metadata
    )

    return {
        "session_id": session_name,
        "room_name": session.room_name,
        "token": token,
        "server_url": livekit_utils.get_server_url()
    }

@frappe.whitelist()
def get_token(id):
    """
    Retrieves a new token for an existing session.
    """
    if not frappe.db.exists("Telehealth Video Session", id):
        frappe.local.response.http_status_code = 404
        return {"error": "Not Found", "message": _("Session not found")}
    
    session = frappe.get_doc("Telehealth Video Session", id)
    
    user = frappe.session.user
    role = "patient"
    full_name = frappe.db.get_value("User", user, "full_name") or user
    if "Doctor" in frappe.get_roles(user):
        role = "doctor"

    import json
    metadata = json.dumps({"role": role, "user_id": user, "full_name": full_name})

    token = livekit_utils.generate_token(
        room_name=session.room_name,
        identity=user,
        name=full_name,
        metadata=metadata
    )
    
    return {
        "session_id": session.name,
        "room_name": session.room_name,
        "token": token,
        "server_url": livekit_utils.get_server_url()
    }

@frappe.whitelist()
def get_status(id):
    """
    Retrieves the current status of a video session.
    """
    if not frappe.db.exists("Telehealth Video Session", id):
        frappe.local.response.http_status_code = 404
        return {"error": "Not Found", "message": _("Session not found")}
    
    session = frappe.get_doc("Telehealth Video Session", id)
    
    return {
        "session_id": session.name,
        "status": session.status,
        "started_at": str(session.started_at) if session.started_at else None,
        "ended_at": str(session.ended_at) if session.ended_at else None,
        "duration": session.duration or 0
    }

@frappe.whitelist()
def end_session(id):
    """
    Ends a video session.
    """
    if not frappe.db.exists("Telehealth Video Session", id):
        frappe.local.response.http_status_code = 404
        return {"error": "Not Found", "message": _("Session not found")}
    
    session = frappe.get_doc("Telehealth Video Session", id)
    if session.status != "Ended":
        session.status = "Ended"
        session.ended_at = now_datetime()
        session.save(ignore_permissions=True)
        frappe.db.commit()
        
    return {"message": _("Session ended")}

@frappe.whitelist(allow_guest=True)
def webhook():
    """
    Handles LiveKit webhooks.
    """
    # In production, verify signature here
    settings = livekit_utils.get_livekit_settings()
    token = frappe.get_request_header("Authorization")
    if not token:
        frappe.local.response.http_status_code = 401
        return {"status": "error", "message": "Missing Authorization header"}
        
    body = frappe.request.get_data()
    event_data = livekit_utils.verify_webhook(token, body)
    
    if not event_data:
        frappe.local.response.http_status_code = 401
        return {"status": "error", "message": "Invalid signature"}
    
    event = frappe.local.form_dict
    event_type = event.get("event")
    
    if event_type == "room_finished":
        room_name = event.get("room", {}).get("name")
        session_name = frappe.db.get_value("Telehealth Video Session", {"room_name": room_name}, "name")
        if session_name:
            session = frappe.get_doc("Telehealth Video Session", session_name)
            session.status = "Ended"
            session.ended_at = now_datetime()
            session.save(ignore_permissions=True)
            
            # Trigger background job for AI notes if agent didn't send them
            # frappe.enqueue("telehealth_platform.telehealth.background_jobs.generate_notes.process", session_id=session_name)
    
    elif event_type == "room_started":
        room_name = event.get("room", {}).get("name")
        frappe.logger().info(f"LiveKit Room Started: {room_name}")
        
    elif event_type == "participant_joined":
        room_name = event.get("room", {}).get("name")
        identity = event.get("participant", {}).get("identity")
        frappe.logger().info(f"Participant {identity} joined room {room_name}")
            
    return {"status": "success"}

@frappe.whitelist()
def get_recording(session_id):
    """
    Returns the recording URL for a session.
    """
    recording_name = frappe.db.get_value("Video Recording", {"video_session": session_id}, "name")
    if not recording_name:
        frappe.local.response.http_status_code = 404
        return {"error": "Not Found", "message": _("Recording not found")}
        
    import boto3
    from botocore.exceptions import ClientError
    
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=frappe.conf.get("aws_access_key_id"),
            aws_secret_access_key=frappe.conf.get("aws_secret_access_key"),
            region_name=frappe.conf.get("aws_region_name")
        )
        bucket_name = frappe.conf.get("s3_bucket_name")
        
        # storage_url is expected to be the S3 key in this logic
        key = recording.storage_url
        
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': key},
            ExpiresIn=3600 # 1 hour
        )
        return {
            "recording_url": presigned_url,
            "expires_at": str(frappe.utils.add_to_date(now_datetime(), seconds=3600))
        }
        
    except Exception as e:
        frappe.log_error(f"S3 Presign Error: {str(e)}", "Get Recording")
        # Fallback if config missing or error (e.g. invalid key)
        return {
            "recording_url": recording.storage_url, # Unsafe fallback for dev
            "expires_at": None,
            "warning": "Could not sign URL. Using raw URL."
        }

def cleanup_expired_sessions():
    """
    Background job to expire sessions that are stuck in 'Active' state 
    for more than 24 hours.
    """
    from frappe.utils import add_days
    
    expiry_time = add_days(now_datetime(), -1)
    
    expired_sessions = frappe.get_all("Telehealth Video Session",
        filters={
            "status": "Active",
            "started_at": ["<", expiry_time]
        }
    )
    
    for sess in expired_sessions:
        try:
            doc = frappe.get_doc("Telehealth Video Session", sess.name)
            doc.status = "Expired"
            doc.ended_at = now_datetime() # Or estimated expiry time
            doc.save(ignore_permissions=True)
            frappe.db.commit()
            frappe.log_error(f"Auto-expired session {sess.name}", "Session Cleanup")
        except Exception:
            frappe.log_error(f"Failed to expire session {sess.name}", "Session Cleanup")
