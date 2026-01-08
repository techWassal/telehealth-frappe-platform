import frappe

@frappe.whitelist(allow_guest=True)
def get_patient_fields():
    meta = frappe.get_meta("Patient")
    return [f.fieldname for f in meta.fields if f.reqd]
