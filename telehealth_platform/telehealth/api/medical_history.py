import frappe
from frappe import _
from frappe.utils import now_datetime, getdate

@frappe.whitelist()
def get_medical_history():
    """
    Retrieves the detailed medical history of the currently authenticated patient.
    Wraps existing Patient and child doc data in Frappe Healthcare.
    """
    user_id = frappe.session.user
    patient_name = frappe.db.get_value("Patient", {"user_id": user_id}, "name")
    
    if not patient_name:
        frappe.local.response.http_status_code = 404
        return {"error": "Not Found", "message": _("Patient record not found")}

    patient = frappe.get_doc("Patient", patient_name)
    
    # Map Frappe Healthcare tables to API contract
    medical_history = {
        "chronic_conditions": patient.medical_history or "",
        "allergies": [],
        "current_medications": [],
        "surgeries": [],
        "last_updated": str(patient.modified)
    }

    # 1. Allergies (Assuming 'allergies' table in Patient DocType)
    if hasattr(patient, "allergies"):
        for a in patient.allergies:
            medical_history["allergies"].append({
                "allergen": a.allergen,
                "severity": a.severity or "Moderate",
                "reaction": a.reaction or ""
            })

    # 2. Medications (Assuming 'medications' table in Patient DocType)
    if hasattr(patient, "medications"):
        for m in patient.medications:
            medical_history["current_medications"].append({
                "medication_name": m.medication,
                "dosage": m.dosage or "",
                "frequency": m.periodicity or "",
                "started_at": str(m.start_date) if m.start_date else None
            })

    # 3. Surgeries (Assuming 'surgeries' record or Clinical Procedure link)
    # Using Clinical Procedure as a proxy for surgeries if they are logged there
    procedures = frappe.get_all("Clinical Procedure", 
        filters={"patient": patient_name, "status": "Completed"},
        fields=["name", "procedure_template", "start_date", "notes"])
    
    for p in procedures:
        medical_history["surgeries"].append({
            "procedure_name": p.procedure_template,
            "date": str(p.start_date) if p.start_date else None,
            "hospital": "", # Placeholder
            "notes": p.notes or ""
        })

    return medical_history

@frappe.whitelist()
def update_medical_history(chronic_conditions=None, allergies=None, current_medications=None, surgeries=None):
    """
    Updates the medical history for the currently authenticated patient (self-reported).
    """
    user_id = frappe.session.user
    patient_name = frappe.db.get_value("Patient", {"user_id": user_id}, "name")
    
    if not patient_name:
        frappe.local.response.http_status_code = 404
        return {"error": "Not Found", "message": _("Patient record not found")}

    try:
        patient = frappe.get_doc("Patient", patient_name)
        
        if chronic_conditions is not None:
            patient.medical_history = chronic_conditions
            
        # Update Allergies (Replace existing child table entries)
        if allergies is not None:
            patient.set("allergies", [])
            for a in allergies:
                patient.append("allergies", {
                    "allergen": a.get("allergen"),
                    "severity": a.get("severity"),
                    "reaction": a.get("reaction")
                })

        # Update Medications
        if current_medications is not None:
            patient.set("medications", [])
            for m in current_medications:
                patient.append("medications", {
                    "medication": m.get("medication_name"),
                    "dosage": m.get("dosage"),
                    "periodicity": m.get("frequency"),
                    "start_date": getdate(m.get("started_at")) if m.get("started_at") else None
                })
        
        patient.save(ignore_permissions=True)
        frappe.db.commit()
        
        return get_medical_history()
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {"error": "Internal Error", "message": str(e)}

@frappe.whitelist()
def list_medical_records():
    """
    Retrieves a list of medical records (lab results, imaging, etc.) for the authenticated patient.
    Wraps 'Patient Medical Record' DocType.
    """
    user_id = frappe.session.user
    patient_name = frappe.db.get_value("Patient", {"user_id": user_id}, "name")
    
    if not patient_name:
        frappe.local.response.http_status_code = 404
        return {"error": "Not Found", "message": _("Patient record not found")}

    records = frappe.get_all("Patient Medical Record",
        filters={"patient": patient_name},
        fields=["name", "communication_date", "subject", "reference_doctype", "reference_name"],
        order_by="communication_date desc"
    )

    return [format_medical_record(r) for r in records]

@frappe.whitelist()
def upload_medical_record(record_type, title, file_attachment, date=None, provider=None):
    """
    Uploads a new medical record/document.
    """
    user_id = frappe.session.user
    patient_name = frappe.db.get_value("Patient", {"user_id": user_id}, "name")
    
    if not patient_name:
        frappe.local.response.http_status_code = 404
        return {"error": "Not Found", "message": _("Patient record not found")}

    # Map record_type to Frappe Healthcare reference doctypes if possible
    # For simplicity, we create a Patient Medical Record entry
    record = frappe.get_doc({
        "doctype": "Patient Medical Record",
        "patient": patient_name,
        "communication_date": getdate(date) if date else getdate(),
        "subject": title,
        "custom_record_type": record_type, # Assuming custom field
        "custom_provider": provider,
    })
    
    record.insert(ignore_permissions=True)
    frappe.db.commit()
    
    # Handle File Attachment
    if file_attachment:
        try:
            from frappe.utils.file_manager import save_file
            # If file_attachment is just a string (filename) and the file is in request.files
            # save_file handles it if we pass the right args.
            # Or if it's base64, we need decode.
            # Here assuming standard Frappe file upload behavior where 'file_attachment' 
            # might be the fieldname in a multipart request.
            
            # Check if there's an actual file in the request under this key
            fname = None
            fcontent = None
            
            if hasattr(frappe.request, "files") and "file_attachment" in frappe.request.files:
                 # It's a multipart upload
                 file_obj = frappe.request.files["file_attachment"]
                 fname = file_obj.filename
                 fcontent = file_obj.read()
            else:
                 # Assume it's a base64 string or similar passed in json
                 # For MVP, let's treat it as a potential text content or filename
                 fname = f"{title}.txt" # Fallback
                 fcontent = str(file_attachment)
            
            saved_file = save_file(
                fname=fname,
                content=fcontent,
                dt="Patient Medical Record",
                dn=record.name,
                is_private=1
            )
        except Exception as e:
            frappe.log_error(f"Failed to save file for record {record.name}: {str(e)}", "Medical Record Upload")
            # Don't fail the whole request, just log
    
    return format_medical_record(record)

@frappe.whitelist()
def get_medical_record_detail(id):
    """
    Get detailed medical record.
    """
    if not frappe.db.exists("Patient Medical Record", id):
        frappe.local.response.http_status_code = 404
        return {"error": "Not Found", "message": _("Record not found")}

    record = frappe.get_doc("Patient Medical Record", id)
    
    # Permission Check
    user_id = frappe.session.user
    # Allow if Doctor (simple role check) or if Owner (Patient)
    if "Healthcare Practitioner" in frappe.get_roles(user_id):
        pass # Doctor access logic (could be more granular)
    else:
        patient_name = frappe.db.get_value("Patient", {"user_id": user_id}, "name")
        if record.patient != patient_name:
             frappe.local.response.http_status_code = 403
             return {"error": "Forbidden", "message": _("Not authorized to view this record")}

    return format_medical_record(record)

def format_medical_record(r):
    """
    Helper to map Patient Medical Record to contract schema.
    """
    return {
        "name": r.name,
        "record_type": getattr(r, "custom_record_type", "other"),
        "title": r.subject,
        "file_attachment": "", # Logic to get attachment URL
        "date": str(r.communication_date) if r.communication_date else None,
        "provider": getattr(r, "custom_provider", "")
    }
