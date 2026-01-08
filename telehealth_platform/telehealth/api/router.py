import frappe
from frappe import _

# This module provides simple REST routing for /api/v1 endpoints
# It maps customized URLs to whitelisted functions

# Map of (Method, Path) -> Whitelisted Function string
ROUTES = {
    # Auth
    ("POST", "patients/register"): "telehealth_platform.telehealth.api.patient.register",
    ("POST", "auth/login"): "telehealth_platform.telehealth.api.auth.login",
    
    # Patient Profile
    ("GET", "patients/profile"): "telehealth_platform.telehealth.api.patient.get_profile",
    ("PUT", "patients/profile"): "telehealth_platform.telehealth.api.patient.update_profile",
    
    # Medical History
    ("GET", "patients/medical-history"): "telehealth_platform.telehealth.api.medical_history.get_medical_history",
    ("PUT", "patients/medical-history"): "telehealth_platform.telehealth.api.medical_history.update_medical_history",
    
    # Medical Records
    ("GET", "patients/medical-records"): "telehealth_platform.telehealth.api.medical_history.list_medical_records",
    ("POST", "patients/medical-records"): "telehealth_platform.telehealth.api.medical_history.upload_medical_record",
    
    # Doctor Search
    ("GET", "doctors/search"): "telehealth_platform.telehealth.api.doctor.search",
    
    # Video Session
    ("POST", "video-session/create"): "telehealth_platform.telehealth.api.video_session.create",
    ("GET", "video-session/token"): "telehealth_platform.telehealth.api.video_session.get_token",
    ("POST", "video-session/end"): "telehealth_platform.telehealth.api.video_session.end_session",
    ("POST", "webhooks/livekit"): "telehealth_platform.telehealth.api.video_session.webhook",
    
    # AI Agents
    ("POST", "transcription/chunk"): "telehealth_platform.telehealth.api.ai.submit_chunk",
    ("GET", "clinical-notes"): "telehealth_platform.telehealth.api.ai.get_clinical_notes",
    ("PUT", "clinical-notes"): "telehealth_platform.telehealth.api.ai.update_clinical_notes",
    ("POST", "clinical-notes/finalize"): "telehealth_platform.telehealth.api.ai.finalize_notes",
    
    # Missing Routes Added
    ("POST", "auth/2fa/verify"): "telehealth_platform.telehealth.api.auth.verify_2fa",
    ("POST", "auth/password-reset/confirm"): "telehealth_platform.telehealth.api.auth.confirm_password_reset",
    
    ("GET", "appointments"): "telehealth_platform.telehealth.api.appointment.list_appointments",
    ("POST", "appointments"): "telehealth_platform.telehealth.api.appointment.book_appointment",
    
    ("POST", "doctors/availability"): "telehealth_platform.telehealth.api.doctor.set_availability",
    
    ("PUT", "insurance/verification"): "telehealth_platform.telehealth.api.insurance.update_details",
    
    ("GET", "admin/audit-logs"): "telehealth_platform.telehealth.api.audit.search_logs",
}

@frappe.whitelist(allow_guest=True)
def handle(path):
    """
    Dispatcher for /api/v1 requests.
    Usage: /api/method/telehealth_platform.telehealth.api.router.handle?path=...
    """
    method = frappe.request.method
    
    # Try exact match first
    func_name = ROUTES.get((method, path))
    
    # Handle paths with IDs (e.g., video-session/{id}/token)
    if not func_name:
        parts = path.split("/")
        if len(parts) >= 2:
            # Check for patterns like video-session/{id}/token
            if method == "GET" and len(parts) == 3 and parts[0] == "video-session" and parts[2] == "token":
                func_name = ROUTES.get(("GET", "video-session/token"))
                frappe.form_dict["id"] = parts[1]
            elif method == "PUT" and len(parts) == 2 and parts[0] == "clinical-notes":
                # PUT /clinical-notes/{id}
                func_name = ROUTES.get(("PUT", "clinical-notes"))
                frappe.form_dict["session_id"] = parts[1]
            elif method == "POST" and len(parts) == 3 and parts[0] == "clinical-notes" and parts[2] == "finalize":
                # POST /clinical-notes/{id}/finalize
                func_name = ROUTES.get(("POST", "clinical-notes/finalize"))
                frappe.form_dict["session_id"] = parts[1]
            elif method == "GET" and parts[0] == "clinical-notes" and len(parts) == 2:
                func_name = ROUTES.get(("GET", "clinical-notes"))
                frappe.form_dict["session_id"] = parts[1]
            elif method == "GET" and parts[0] == "appointments" and len(parts) == 2:
                # GET /appointments/{id}
                func_name = "telehealth_platform.telehealth.api.appointment.get_appointment_details"
                frappe.form_dict["id"] = parts[1]
            elif method == "GET" and parts[0] == "admin" and parts[1] == "audit-logs" and len(parts) == 3:
                 # GET /admin/audit-logs/{id} - Assuming audit detail uses this pattern or query param?
                 # Contract check: audit-api.yaml says GET /admin/audit-logs/{id}
                 func_name = "telehealth_platform.telehealth.api.audit.get_log_detail"
                 frappe.form_dict["id"] = parts[2]
            elif method == "GET" and parts[0] == "doctors" and parts[2] == "availability" and len(parts) == 3:
                 # GET /doctors/{id}/availability
                 func_name = "telehealth_platform.telehealth.api.doctor.get_availability"
                 frappe.form_dict["id"] = parts[1]
    
    if not func_name:
        frappe.local.response.http_status_code = 404
        return {"error": "Not Found", "message": f"Route {method} {path} not found"}

    # Execute the whitelisted method
    args = frappe.form_dict.copy()
    args.pop("path", None)
    return frappe.call(func_name, **args)
