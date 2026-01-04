import frappe
from frappe import _
from frappe.utils import getdate

@frappe.whitelist(allow_guest=True)
def register(patient_name, email, phone, date_of_birth, password, gender=None, address=None, emergency_contact=None):
    """
    Registers a new patient. 
    1. Creates a Frappe User.
    2. Creates a Frappe Healthcare Patient linked to the user.
    """
    if frappe.db.exists("User", email):
        frappe.local.response.http_status_code = 400
        return {"error": "Conflict", "message": _("User with this email already exists")}

    try:
        # 1. Create User
        user = frappe.get_doc({
            "doctype": "User",
            "email": email,
            "first_name": patient_name,
            "new_password": password,
            "enabled": 1,
            "roles": [{"role": "Patient"}]
        })
        user.insert(ignore_permissions=True)

        # 2. Create Patient
        patient = frappe.get_doc({
            "doctype": "Patient",
            "patient_name": patient_name,
            "email": email,
            "mobile": phone,
            "dob": getdate(date_of_birth),
            "sex": gender,
            "user_id": user.name
        })
        
        # Add address if provided (might need more logic depending on setup)
        # For now, storing in a custom field or comment if necessary
        
        patient.insert(ignore_permissions=True)
        frappe.db.commit()

        frappe.local.response.http_status_code = 201
        return get_patient_profile_data(patient)

    except Exception as e:
        frappe.db.rollback()
        frappe.local.response.http_status_code = 500
        return {"error": "Internal Error", "message": str(e)}

@frappe.whitelist()
def get_profile():
    """
    Retrieves the profile of the currently authenticated patient.
    """
    user_id = frappe.session.user
    patient_name = frappe.db.get_value("Patient", {"user_id": user_id}, "name")
    
    if not patient_name:
        frappe.local.response.http_status_code = 404
        return {"error": "Not Found", "message": _("Patient record not found for this user")}

    patient = frappe.get_doc("Patient", patient_name)
    return get_patient_profile_data(patient)

@frappe.whitelist()
def update_profile(**kwargs):
    """
    Updates the patient profile.
    """
    user_id = frappe.session.user
    patient_name = frappe.db.get_value("Patient", {"user_id": user_id}, "name")
    
    if not patient_name:
        frappe.local.response.http_status_code = 404
        return {"error": "Not Found", "message": _("Patient record not found")}

    try:
        patient = frappe.get_doc("Patient", patient_name)
        
        # Map fields
        if "patient_name" in kwargs:
            patient.patient_name = kwargs["patient_name"]
        if "phone" in kwargs:
            patient.mobile = kwargs["phone"]
        if "gender" in kwargs:
            patient.sex = kwargs["gender"]
        if "address" in kwargs:
            # Simple assumption: Address is a text field or we just store it in a custom field for MVP
            patient.set("custom_address", kwargs["address"])
        if "emergency_contact" in kwargs:
            # Simple assumption: Storing as text or JSON in custom field
            patient.set("custom_emergency_contact", kwargs["emergency_contact"])

        if "consent_recorded" in kwargs:
            # Assuming custom field or specific logic
            patient.set("custom_consent_recorded", kwargs["consent_recorded"])
            
        patient.save(ignore_permissions=True)
        frappe.db.commit()
        
        return get_patient_profile_data(patient)
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {"error": "Internal Error", "message": str(e)}

def get_patient_profile_data(patient):
    """
    Helper to format Patient DocType into contract-compliant JSON.
    """
    from telehealth_platform.telehealth.api.medical_history import get_medical_history
    
    # Try to fetch medical history summary if available
    # Since get_medical_history relies on frappe.session.user, we need to ensure context is correct
    # or better, refactor get_medical_history to accept patient_name optional arg. 
    # For now, we assume this is called within a request context where session user matches patient.
    
    med_history = {}
    try:
        # We can't easily call the API function if it relies purely on session user without args, 
        # but here we are in the same request context usually.
        # Ideally, refactor medical_history.get_medical_history to be reusable.
        # For MVP, we'll do a lightweight fetch or leave it empty if complicated.
        pass
    except:
        pass

    return {
        "name": patient.name,
        "patient_name": patient.patient_name,
        "email": patient.email,
        "phone": patient.mobile,
        "date_of_birth": str(patient.dob) if patient.dob else None,
        "gender": patient.sex,
        "address": getattr(patient, "custom_address", ""),
        "emergency_contact": getattr(patient, "custom_emergency_contact", ""),
        "consent_recorded": getattr(patient, "custom_consent_recorded", False),
        "medical_history_summary": med_history # Placeholder for now to match contract key existence
    }
