import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

@frappe.whitelist()
def create_medication_request(patient, medication, dosage, periodicity, encounter=None, practitioner=None):
    """
    Creates a new Medication Request (standard Frappe Health DocType).
    """
    if not frappe.has_permission("Medication Request", "create"):
        frappe.throw(_("Not authorized to create Medication Requests"), frappe.PermissionError)

    if not practitioner:
        practitioner = frappe.db.get_value("Healthcare Practitioner", {"user_id": frappe.session.user}, "name")
        if not practitioner:
            frappe.throw(_("Healthcare Practitioner record not found for this user"))

    request = frappe.get_doc({
        "doctype": "Medication Request",
        "patient": patient,
        "practitioner": practitioner,
        "encounter": encounter,
        "medication": medication,
        "dosage": dosage,
        "periodicity": periodicity,
        "status": "Active",
        "intent": "Order",
        "priority": "Routine",
        "authored_on": now_datetime()
    })

    request.insert()
    frappe.db.commit()

    return request.as_dict()

@frappe.whitelist()
def list_active_medications(patient):
    """
    Lists active Medication Requests for a patient.
    """
    medications = frappe.get_all("Medication Request",
        filters={
            "patient": patient,
            "status": "Active"
        },
        fields=["name", "medication", "dosage", "periodicity", "authored_on"]
    )
    return medications

@frappe.whitelist()
def search_medications(text):
    """
    Searches for medications in the Medication DocType.
    """
    return frappe.get_all("Medication",
        filters={"name": ["like", f"%{text}%"]},
        fields=["name"],
        limit=20
    )

@frappe.whitelist()
def check_allergies(patient, medication):
    """
    Checks if a patient is allergic to a specific medication.
    """
    patient_doc = frappe.get_doc("Patient", patient)
    allergies = []
    
    if hasattr(patient_doc, "allergies"):
        for a in patient_doc.allergies:
            # Simple substring match for MVP
            if medication.lower() in a.allergen.lower() or a.allergen.lower() in medication.lower():
                allergies.append({
                    "allergen": a.allergen,
                    "severity": a.severity,
                    "reaction": a.reaction
                })
    
    return allergies
