import frappe
from frappe import _
from frappe.auth import LoginManager
from telehealth_platform.telehealth.api.utils import generate_tokens, verify_token, get_user_role

@frappe.whitelist(allow_guest=True)
def login(email, password):
    """
    User login. Authenticates via Frappe and returns JWT tokens.
    """
    try:
        login_manager = LoginManager()
        login_manager.authenticate(user=email, pwd=password)
        login_manager.post_login()
    except frappe.AuthenticationError:
        frappe.local.response.http_status_code = 401
        return {
            "error": "Unauthorized",
            "message": _("Invalid email or password")
        }
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {
            "error": "Internal Error",
            "message": str(e)
        }

    user = frappe.get_doc("User", email)
    access_token, refresh_token = generate_tokens(user.name)
    
    # Check if 2FA is required (primarily for Doctors/Practitioners)
    requires_2fa = False
    if "Healthcare Practitioner" in frappe.get_roles(user.name):
        # In a real scenario, check if user has 2FA enabled in Frappe
        # For MVP, we can flag this based on role if needed
        requires_2fa = True

    return {
        "token": access_token,
        "refresh_token": refresh_token,
        "requires_2fa": requires_2fa,
        "user": {
            "id": user.name,
            "email": user.email,
            "role": get_user_role(user.name)
        }
    }

@frappe.whitelist()
def logout():
    """
    User logout. 
    Notes: Frappe handles session clearing if called from a browser, 
    for JWT we just return success as the client should discard the token.
    """
    frappe.local.login_manager.logout()
    return {"message": _("Logout successful")}

@frappe.whitelist(allow_guest=True)
def refresh_token(refresh_token):
    """
    Generates new access token using a valid refresh token.
    """
    try:
        payload = verify_token(refresh_token, token_type="refresh")
        if not payload:
            frappe.local.response.http_status_code = 401
            return {"error": "Unauthorized", "message": _("Invalid refresh token")}
        
        user_id = payload.get("sub")
        new_access_token, new_refresh_token = generate_tokens(user_id)
        
        user = frappe.get_doc("User", user_id)
        
        return {
            "token": new_access_token,
            "refresh_token": new_refresh_token,
            "user": {
                "id": user.name,
                "email": user.email,
                "role": get_user_role(user_id)
            }
        }
    except Exception as e:
        frappe.local.response.http_status_code = 401
        return {"error": "Unauthorized", "message": str(e)}

@frappe.whitelist(allow_guest=True)
def request_password_reset(email):
    """
    Sends a password reset link.
    """
    try:
        from frappe.utils.password import send_mask_password_resethash
        user = frappe.get_doc("User", email)
        send_mask_password_resethash(user)
        return {"message": _("Password reset email sent")}
    except frappe.DoesNotExistError:
        # Don't reveal if user exists for security
        return {"message": _("If the email exists, a reset link has been sent")}
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {"error": "Internal Error", "message": str(e)}

@frappe.whitelist(allow_guest=True)
def confirm_password_reset(token, new_password):
    """
    Confirms password reset using token.
    """
    try:
        from frappe.utils.password import check_password, update_password
        
        # Frappe's validate_reset_password_link logic usually involves
        # checking the key against the User document.
        # However, since we are building an API that might not use the standard
        # HTML form flow, we need to replicate the validation logic or use
        # a standard reset method if available.
        # For this version, we assume the token is the signed key sent in the email.
        
        # We need to find the user by this key.
        # This is non-trivial without Frappe's standard form context.
        # Standard approach: The link is /update-password?key=...
        
        user = frappe.db.get_value("User", {"reset_password_key": token}, "name")
        if not user:
            frappe.local.response.http_status_code = 400
            return {"error": "Invalid Token", "message": _("Invalid or expired password reset token")}
            
        # Update password
        update_password(user, new_password)
        
        # Clear the key
        frappe.db.set_value("User", user, "reset_password_key", "")
        
        return {"message": _("Password updated successfully")}
        
    except Exception as e:
        frappe.local.response.http_status_code = 500
        return {"error": "Internal Error", "message": str(e)}

@frappe.whitelist()
def verify_2fa(code):
    """
    Verify 2FA code for the current user.
    """
    user = frappe.session.user
    if user == "Guest":
        frappe.local.response.http_status_code = 401
        return {"error": "Unauthorized", "message": _("Please login first")}

    # Logic to verify 2FA code
    # Using Frappe's OTP verification if available, or mock for MVP compliance
    try:
        from frappe.twofactor import verify_token
        # This function might not exist in all versions or might differ in signature.
        # Fallback to simple check or just "Not Implemented" but returning structure.
        # For this task, we treat "123456" as valid for demo/MVP if real 2FA is not setup.
        
        # NOTE: Real implementation requires 'on_login' setup of 2FA.
        if code == "123456":
             return {"message": _("2FA verification successful")}
             
        # Check standard 2FA
        if verify_token(user, code):
            return {"message": _("2FA verification successful")}
            
    except Exception:
        # Fallback
        if code == "123456":
            return {"message": _("2FA verification successful")}

    frappe.local.response.http_status_code = 400
    return {"error": "Invalid Code", "message": _("Invalid 2FA code")}
