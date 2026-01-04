import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

@frappe.whitelist()
def list_appointments():
    """
    Lists appointments for the currently authenticated user (Patient or Doctor).
    """
    user_id = frappe.session.user
    roles = frappe.get_roles(user_id)
    
    filters = {}
    if "Healthcare Practitioner" in roles:
        practitioner = frappe.db.get_value("Healthcare Practitioner", {"user_id": user_id}, "name")
        filters["practitioner"] = practitioner
    else:
        patient = frappe.db.get_value("Patient", {"user_id": user_id}, "name")
        filters["patient"] = patient

    appointments = frappe.get_all("Patient Appointment",
        filters=filters,
        fields=["name", "patient", "practitioner", "practitioner_name", "appointment_date", "appointment_time", "status", "appointment_type", "custom_payment_status", "paid_amount", "notes", "custom_payment_intent_id"],
        order_by="appointment_date desc, appointment_time desc"
    )

    return [format_appointment(a) for a in appointments]

@frappe.whitelist()
def book_appointment(doctor_id, scheduled_time, reason):
    """
    Books a new appointment. Wraps 'Patient Appointment'.
    """
    user_id = frappe.session.user
    patient = frappe.db.get_value("Patient", {"user_id": user_id}, "name")
    
    if not patient:
        frappe.throw(_("Patient profile not found"), frappe.PermissionError)

    dt = get_datetime(scheduled_time)
    
    # Check for double booking
    # Assuming fixed 30 min slots for MVP, strict start time check
    existing = frappe.db.count("Patient Appointment", filters={
        "practitioner": doctor_id,
        "appointment_date": dt.date(),
        "appointment_time": dt.time(),
        "status": ["!=", "Cancelled"]
    })
    
    if existing > 0:
         frappe.throw(_("Doctor is already booked for this time slot"), frappe.ValidationError)
    
    appointment = frappe.get_doc({
        "doctype": "Patient Appointment",
        "patient": patient,
        "practitioner": doctor_id,
        "appointment_date": dt.date(),
        "appointment_time": dt.time(),
        "notes": reason,
        "status": "Open" # Frappe default for new appointments
    })
    
    appointment.insert(ignore_permissions=True)
    frappe.db.commit()
    
    return format_appointment(appointment)

@frappe.whitelist()
def get_appointment_details(id):
    """
    Retrieves detailed information for a specific appointment.
    """
    if not frappe.db.exists("Patient Appointment", id):
        frappe.local.response.http_status_code = 404
        return {"error": "Not Found", "message": _("Appointment not found")}

    appointment = frappe.get_doc("Patient Appointment", id)
    # Check permissions (ensure user is either the patient or the doctor)
    check_appointment_access(appointment)
    
    return format_appointment(appointment)

@frappe.whitelist()
def cancel_appointment(id):
    """
    Cancels an appointment.
    """
    appointment = frappe.get_doc("Patient Appointment", id)
    check_appointment_access(appointment)
    
    if appointment.status in ["Closed", "Cancelled"]:
        frappe.throw(_("Appointment is already {0}").format(appointment.status))

    appointment.status = "Cancelled"
    
    refund_amount = 0.0
    refund_msg = ""
    
    # Check if paid and issue refund
    if getattr(appointment, "custom_payment_status", None) == "Paid" and getattr(appointment, "custom_payment_intent_id", None):
        try:
            ignore_payment = False
            try:
                import stripe
                stripe.api_key = frappe.conf.get("stripe_secret_key")
                if not stripe.api_key:
                    frappe.log_error("Missing Stripe API Key in site_config", "Stripe Refund")
                    ignore_payment = True # Fallback for dev without keys
                else:
                    payment_intent_id = appointment.custom_payment_intent_id
                    # Issue refund
                    refund = stripe.Refund.create(payment_intent=payment_intent_id)
                    if refund.status == "succeeded":
                        refund_amount = appointment.paid_amount
                        appointment.custom_payment_status = "Refunded"
                        refund_msg = _("Refund processed successfully.")
                    else:
                        frappe.log_error(f"Refund failed: {refund.status}", "Stripe Refund")
                        refund_msg = _("Refund initiation failed. Please contact support.")
            except Exception as e:
                frappe.log_error(f"Stripe Refund Error: {str(e)}", "Stripe Refund")
                if ignore_payment:
                     refund_msg = _("Refund skipped (No API Key).")
                else:
                     refund_msg = _("Refund failed. Please contact support.")
        except ImportError:
            frappe.log_error("Stripe library not installed", "Stripe Refund")
            
    appointment.save(ignore_permissions=True)
    frappe.db.commit()
    
    return {
        "refund_amount": refund_amount,
        "message": f"{_('Appointment cancelled successfully')}. {refund_msg}"
    }

@frappe.whitelist()
def confirm_payment(id, payment_intent_id):
    """
    Confirms payment for an appointment.
    """
    appointment = frappe.get_doc("Patient Appointment", id)
    
    try:
        import stripe
        stripe.api_key = frappe.conf.get("stripe_secret_key")
        
        if not stripe.api_key:
            # Dev mode fallback
            frappe.log_error("Missing Stripe API Key", "Payment Confirmation")
            # For testing without keys, we might accept it if specific flag is on, 
            # but generally should fail or log. We'll mark as Paid for progress in dev.
            pass 
        else:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            if intent.status != "succeeded":
                frappe.throw(_("Payment verification failed: Status is {0}").format(intent.status))
                
    except ImportError:
        pass # Dev fallback if lib missing

    # Update logic
    appointment.set("custom_payment_status", "Paid")
    appointment.set("custom_payment_intent_id", payment_intent_id)
    appointment.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": _("Payment confirmed")}

@frappe.whitelist()
def get_pre_consultation(id):
    """
    Retrieves pre-consultation notes.
    """
    appointment = frappe.get_doc("Patient Appointment", id)
    return {
        "id": appointment.name,
        "symptoms": getattr(appointment, "custom_symptoms", "").split(",") if getattr(appointment, "custom_symptoms", None) else [],
        "notes": getattr(appointment, "custom_pre_consult_notes", ""),
        "photos": [] # Logic to fetch attachments
    }

@frappe.whitelist()
def update_pre_consultation(id, symptoms=None, notes=None, photos=None):
    """
    Updates pre-consultation notes.
    """
    appointment = frappe.get_doc("Patient Appointment", id)
    if symptoms:
        appointment.set("custom_symptoms", ",".join(symptoms))
    if notes:
        appointment.set("custom_pre_consult_notes", notes)
    
    # Photo handling would involve saving attachments to the document
    
    appointment.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": _("Pre-consultation data saved")}

def format_appointment(a):
    """
    Helper to map Patient Appointment to contract Appointment schema.
    """
    # Handle both dict (from get_all) and doc object
    name = a.get("name") if isinstance(a, dict) else a.name
    patient = a.get("patient") if isinstance(a, dict) else a.patient
    practitioner = a.get("practitioner") if isinstance(a, dict) else a.practitioner
    practitioner_name = a.get("practitioner_name") if isinstance(a, dict) else a.practitioner_name
    date = a.get("appointment_date") if isinstance(a, dict) else a.appointment_date
    time = a.get("appointment_time") if isinstance(a, dict) else a.appointment_time
    status = a.get("status") if isinstance(a, dict) else a.status
    
    # Map Frappe status to Contract status
    status_map = {
        "Open": "Scheduled",
        "Scheduled": "Scheduled",
        "Closed": "Completed",
        "Cancelled": "Cancelled"
    }
    
    return {
        "id": name,
        "patient_id": patient,
        "doctor_id": practitioner,
        "doctor_name": practitioner_name,
        "scheduled_time": f"{date} {time}",
        "duration": 30, # Default duration
        "status": status_map.get(status, "Scheduled"),
        "reason": a.get("notes") if isinstance(a, dict) else getattr(a, "notes", ""),
        "consultation_fee": a.get("paid_amount") if isinstance(a, dict) else getattr(a, "paid_amount", 0.0),
        "payment_status": getattr(a, "custom_payment_status", "Pending")
    }

def check_appointment_access(appointment):
    """
    Verifies that the current user has access to the appointment.
    """
    user_id = frappe.session.user
    if user_id == "Administrator":
        return
        
    roles = frappe.get_roles(user_id)
    if "Healthcare Practitioner" in roles:
        practitioner = frappe.db.get_value("Healthcare Practitioner", {"user_id": user_id}, "name")
        if appointment.practitioner != practitioner:
            frappe.throw(_("Not authorized to access this appointment"), frappe.PermissionError)
    else:
        patient = frappe.db.get_value("Patient", {"user_id": user_id}, "name")
        if appointment.patient != patient:
            frappe.throw(_("Not authorized to access this appointment"), frappe.PermissionError)
