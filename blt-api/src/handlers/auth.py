
import hashlib
import secrets
import time
from typing import Any, Dict, Optional

from libs.db import get_db_safe
from utils import parse_json_body, error_response, cors_headers, check_required_fields, json_response, convert_single_d1_result, extract_id_from_result
from libs.constant import __HASHING_ITERATIONS, __HASHING_ALGORITHM
from libs.jwt_utils import create_access_token
from services.email_service import EmailService

import logging
def generate_jwt_token(user_id: int, secret: str, expires_in: int = 3600) -> str:
    """Generate a JWT token for the given user ID."""
    payload = {
        "user_id": user_id,
        "exp": int(time.time()) + expires_in
    }
    token = create_access_token(payload, secret)
    return token

async def handle_signup(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """Handle user signup/registration."""
    base_url = env.BLT_API_BASE_URL if hasattr(env, 'BLT_API_BASE_URL') else "http://localhost:8787"
    method = str(request.method).upper()
    logger = logging.getLogger(__name__)
    if method != "POST":
        return error_response( "Method Not Allowed", 404)
    try: 
        body = await parse_json_body(request)
        if not body:
            return error_response("Invalid JSON body", 400)

        required_fields = ["username", "password", "email"]

        valid, missing_field = await check_required_fields(body, required_fields)

        if not valid:
            return error_response("Missing required field",400)
        
        
        # getting db connection
        try :
            db = await get_db_safe(env)
        except Exception as e:       
            return error_response("Database connection error", 500)

        # Check if username or email already exists
        stmt = await db.prepare("SELECT id FROM users WHERE username = ? OR email = ?").bind(body["username"], body["email"]).first()
        existing_user = None
        if stmt:
            existing_user = stmt.to_py() if hasattr(stmt, 'to_py') else dict(stmt)

        if existing_user:
            return error_response("User already exists", 400)

        # Hash the password using PBKDF2
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', body["password"].encode('utf-8'), salt.encode('utf-8'), 100000)
        hashed_password = f"{salt}${password_hash.hex()}"

        # Insert the new user into the database
        result = await db.prepare("INSERT INTO users (username, email, password, is_active) VALUES (?, ?, ?, ?)").bind(body["username"], body["email"], hashed_password, False).run()
        
        # Get the last inserted ID
        last_id_result = await db.prepare('SELECT last_insert_rowid() as id').first()
        user_id = extract_id_from_result(last_id_result, 'id')

        # send verification email here using sendgrid
        email_service = EmailService(
            api_key=env.SENDGRID_API_KEY,
            from_email="kaif@post0.live",
            from_name="OWASP BLT"
        )
        token = generate_jwt_token(user_id, env.JWT_SECRET, expires_in=10*60)  # Token valid for 10 minutes
        base_url = env.BLT_WEBSITE_URL
        
        status, response = await email_service.send_verification_email(
            to_email=body["email"],
            username=body["username"],
            verification_token=token,
            base_url=base_url
        )
        
        if status >= 400:
            logger.error(f"Failed to send verification email: {response}")
        
        return json_response({"message": "User registered successfully, To activate your account, please check your email for the verification link.", "user_id": user_id}, status=201, headers=cors_headers())

    except Exception as e:
        logger.error("Error during signup: %s", str(e))
        return error_response("Internal Server Error", 500)
    

async def handle_signin(request: Any, env: Any, path_params: Dict[str, str], query_params: Dict[str, str], path: str) -> Any:
    """Handle user login/authentication."""
    logger = logging.getLogger(__name__)
    try:
        jwt_secret = env.JWT_SECRET
        if not jwt_secret:
            return error_response("JWT secret not configured, please configure it using `wrangler secret put JWT_SECRET`", 500)
        method = str(request.method).upper()
        if method != "POST":
            return error_response("Method Not Allowed", 404)
        body = await parse_json_body(request)
        if not body:
            return error_response("Invalid JSON body", 400) 
        required_fields = ["username", "password"]
        valid, missing_field = await check_required_fields(body, required_fields)
        if not valid:
            return error_response("Missing required field", 400)
        # getting db connection
        try:
            db = await get_db_safe(env)
        except Exception as e:
            return error_response("Database connection error", 500)
        
        # Fetch user by username    
        stmt = await db.prepare("SELECT id, password FROM users WHERE username = ?").bind(body["username"]).first()
        
        
        user = await convert_single_d1_result(stmt) if stmt else None
        if user == None or "password" not in user:
            return error_response("Invalid username or password", 401)
        stored_password = user["password"]
        
        # Verify the password
        salt, stored_hash = stored_password.split('$')
        password_hash = hashlib.pbkdf2_hmac('sha256', body["password"].encode('utf-8'), salt.encode('utf-8'), __HASHING_ITERATIONS).hex()
        if password_hash != stored_hash:
            return error_response("Invalid username or password", 401)
        
        # Create JWT token with 24 hour expiration
        token = create_access_token(
            {"user_id": user["id"]}, 
            jwt_secret, 
            expires_in=24 * 3600  # 24 hour expiration
        )

        json_response_data = {
            "message": "Login successful",
            "token": token
        }
        return json_response(json_response_data, status=200, headers=cors_headers())

    except Exception as e:
        logger.error("Error during login: %s", str(e))
        return error_response("Internal Server Error", 500)


async def handle_verify_email(request: Any, env: Any, path_params: Dict[str, str], query_params: Dict[str, str], path: str) -> Any: 
    """Handle email verification."""
    logger = logging.getLogger(__name__)   
    try:
        db= await  get_db_safe(env)
        jwt_secret = env.JWT_SECRET

        if not jwt_secret:
            return error_response("JWT secret not configured, please configure it using `wrangler secret put JWT_SECRET`", 500)

        method = str(request.method).upper()
        if method != "GET":
            return error_response("Method Not Allowed", 404)
        
        token = path_params.get("token")
        if not token:
            return error_response("Missing token", 400)
        
        # Verify the token and extract user ID
        payload = create_access_token.verify_token(token, jwt_secret)
        if not payload or "user_id" not in payload:
            return error_response("Invalid or expired token", 400)
        
        user_id = payload["user_id"]

        # Activate the user's account
        await db.prepare("UPDATE users SET is_active = ? WHERE id = ?").bind(True, user_id).run()

        return json_response({"message": "Email verified successfully, your account is now active."}, status=200, headers=cors_headers())

    except Exception as e:
        
        logger.error("Error during email verification: %s", str(e))
        return error_response("Internal Server Error", 500)