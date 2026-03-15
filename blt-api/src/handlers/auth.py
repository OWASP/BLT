
import hashlib
import secrets
import time
from typing import Any, Dict, Optional

from libs.db import get_db_safe
from utils import parse_json_body, error_response, cors_headers, check_required_fields, extract_id_from_result
from libs.constant import __HASHING_ITERATIONS
from libs.jwt_utils import create_access_token, decode_jwt
from services.email_service import EmailService
from workers import Response
from models import User

import logging
def generate_jwt_token(user_id: int, secret: str, expires_in: int = 3600) -> str:
    """
    Generate a JWT authentication token for a user.
    
    Creates a signed JWT token containing the user ID and expiration time,
    used for authenticating API requests.
    
    Args:
        user_id: The database ID of the user
        secret: JWT secret key for signing the token (from env.JWT_SECRET)
        expires_in: Token validity duration in seconds (default: 1 hour)
    
    Returns:
        Signed JWT token string that can be used in Authorization headers
    """
    payload = {
        "user_id": user_id,
        "exp": int(time.time()) + expires_in
    }
    token = create_access_token(payload, secret, expires_in=expires_in)
    return token

async def handle_signup(
    request: Any,
    env: Any,
    path_params: Dict[str, str],
    query_params: Dict[str, str],
    path: str
) -> Any:
    """
    Handle user registration/signup endpoint (POST /auth/signup).
    
    Creates a new user account with hashed password (PBKDF2-SHA256),
    sends verification email via Mailgun, and returns success response.
    
    Required fields in request body:
        - username: Unique username for the account
        - email: User email address (must be unique)
        - password: Plain text password (will be hashed with salt)
    
    Process:
        1. Validates request method and required fields
        2. Checks for existing username/email
        3. Hashes password with random salt using PBKDF2
        4. Inserts user into database with is_active=false
        5. Generates verification JWT token (10 min expiry)
        6. Sends verification email with token link
    
    Returns:
        201 Created with message to check email for verification link,
        or 400/500 error if validation fails or user exists
    """
    base_url = env.BLT_API_BASE_URL if hasattr(env, 'BLT_API_BASE_URL') else "http://localhost:8787"
    method = str(request.method).upper()
    logger = logging.getLogger(__name__)
    if method != "POST":
        return error_response( "Method Not Allowed", 405)
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
        existing_user = await User.objects(db).filter(username=body["username"]).first()
        if not existing_user:
            existing_user = await User.objects(db).filter(email=body["email"]).first()

        if existing_user:
            return error_response("User already exists", 400)

        # Hash the password using PBKDF2
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', body["password"].encode('utf-8'), salt.encode('utf-8'), __HASHING_ITERATIONS)
        hashed_password = f"{salt}${password_hash.hex()}"

        # Insert the new user into the database
        new_user = await User.create(db, username=body["username"], email=body["email"], password=hashed_password, is_active=False)
        user_id = new_user.get("id") if new_user else None

        # send verification email here using Mailgun
        email_service = EmailService(
            api_key=env.MAILGUN_API_KEY,
            domain=env.MAILGUN_DOMAIN,
            from_email=f"postmaster@{env.MAILGUN_DOMAIN}",
            from_name="OWASP BLT"
        )
        token = generate_jwt_token(user_id, env.JWT_SECRET, expires_in=10*60)  # Token valid for 10 minutes
        base_url = env.BLT_API_BASE_URL
        
        status, response = await email_service.send_verification_email(
            to_email=body["email"],
            username=body["username"],
            verification_token=token,
            base_url=base_url
        )
        
        if status >= 400:
            logger.error(f"Failed to send verification email: {response}")
        
        return Response.json({"message": "User registered successfully, To activate your account, please check your email for the verification link.", "user_id": user_id}, status=201, headers=cors_headers())

    except Exception as e:
        logger.error("Error during signup: %s", str(e))
        return error_response("Internal Server Error", 500)
    

async def handle_signin(request: Any, env: Any, path_params: Dict[str, str], query_params: Dict[str, str], path: str) -> Any:
    """
    Handle user authentication/login endpoint (POST /auth/signin).
    
    Validates user credentials and returns a JWT token for authenticated API access.
    
    Required fields in request body:
        - username: User's username
        - password: Plain text password to verify
    
    Process:
        1. Validates request method and required fields
        2. Fetches user record by username from database
        3. Verifies password using PBKDF2-SHA256 with stored salt
        4. Generates JWT access token (24 hour expiry)
        5. Returns token for use in Authorization header
    
    Returns:
        200 OK with JWT token on successful authentication,
        or 401/400/500 error for invalid credentials or server issues
    """
    logger = logging.getLogger(__name__)
    try:
        jwt_secret = env.JWT_SECRET
        if not jwt_secret:
            return error_response("JWT secret not configured, please configure it using `wrangler secret put JWT_SECRET`", 500)
        method = str(request.method).upper()
        if method != "POST":
            return error_response("Method Not Allowed", 405)
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
        user = await User.objects(db).filter(username=body["username"]).first()

        if user is None or "password" not in user:
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

        res = {
            "message": "Login successful",
            "token": token
        }
        return Response.json(res, status=200, headers=cors_headers())

    except Exception as e:
        logger.error("Error during login: %s", str(e))
        return error_response("Internal Server Error", 500)


async def handle_verify_email(request: Any, env: Any, path_params: Dict[str, str], query_params: Dict[str, str], path: str) -> Any:
    """
    Handle email verification endpoint (GET /auth/verify-email).
    
    Validates the JWT token from the verification email link and activates the user account.
    This endpoint is accessed via the link sent in the signup verification email.
    
    Required query parameter:
        - token: JWT token containing user_id and expiration (10 min validity)
    
    Process:
        1. Validates request method is GET
        2. Extracts and decodes JWT token from query params
        3. Verifies token signature and expiration
        4. Activates user account by setting is_active=true
        5. Returns success confirmation
    
    Returns:
        200 OK with success message when email is verified,
        or 400/500 error for invalid/expired tokens or server issues
    """ 
    logger = logging.getLogger(__name__)   
    try:
        db= await  get_db_safe(env)
        jwt_secret = env.JWT_SECRET

        if not jwt_secret:
            return error_response("JWT secret not configured, please configure it using `wrangler secret put JWT_SECRET`", 500)

        method = str(request.method).upper()
        if method != "GET":
            return error_response("Method Not Allowed", 405)
        
        # Get token from query parameters (e.g., ?token=xxx)
        token = query_params.get("token")
        if not token:
            return error_response("Missing token", 400)
        
        # Verify the token and extract user ID
        payload = decode_jwt(token, jwt_secret)
        if not payload or "user_id" not in payload:
            return error_response("Invalid or expired token", 400)
        
        user_id = payload["user_id"]

        # Activate the user's account
        await User.objects(db).filter(id=user_id).update(is_active=True)

        return Response.json({"message": "Email verified successfully, your account is now active."}, status=200, headers=cors_headers())

    except Exception as e:
        
        logger.error("Error during email verification: %s", str(e))
        return error_response("Internal Server Error", 500)