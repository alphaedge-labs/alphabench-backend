from google.oauth2 import id_token
from google.auth.transport import requests
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from fastapi import HTTPException, status
from typing import Tuple, Dict

from src.config.settings import settings
from src.db.base import get_db, execute_query_single
from src.db.queries.subscriptions import get_free_subscription_plan

class GoogleOAuth:
    @staticmethod
    async def verify_token(token: str) -> Dict:
        """Verify Google OAuth token"""
        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )

            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
                
            return idinfo
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )

    @staticmethod
    async def authenticate_user(code: str, current_user_id: str, redirect_uri: str, db) -> Tuple[Dict, bool]:
        """Authenticate user with Google OAuth"""
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": settings.GOOGLE_CLIENT_ID,
                        "client_secret": settings.GOOGLE_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                    }
                },
                scopes=[
                    "https://www.googleapis.com/auth/userinfo.email",
                    "https://www.googleapis.com/auth/userinfo.profile",
                    "openid"
                ]
            )
            
            flow.redirect_uri = redirect_uri
            flow.fetch_token(code=code)
            credentials = flow.credentials

            # Verify the token with Google
            user_info = id_token.verify_oauth2_token(
                credentials.id_token,
                requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )

            # Check if user exists by google_id or email first
            with get_db() as conn:
                # First try to find an existing Google user
                user = execute_query_single(
                    conn,
                    """
                    SELECT * FROM users 
                    WHERE google_id = %s OR email = %s
                    """,
                    (user_info['sub'], user_info['email'])
                )
                
                if not user:
                    # Try to find anonymous user from the current session
                    user = execute_query_single(
                        conn,
                        """
                        SELECT * FROM users 
                        WHERE id = %s AND is_anonymous = true
                        """,
                        (current_user_id,)
                    )
                    
                    conn.execute("BEGIN")
                    try:
                        if user:
                            # Update anonymous user with Google info
                            user = execute_query_single(
                                conn,
                                """
                                UPDATE users 
                                SET google_id = %s,
                                    email = %s, 
                                    name = %s,
                                    picture_url = %s,
                                    is_anonymous = false
                                WHERE id = %s
                                RETURNING *
                                """,
                                (user_info['sub'], user_info['email'], user_info['name'], 
                                 user_info['picture'], user['id'])
                            )
                        else:
                            # Create new user
                            user = execute_query_single(
                                conn,
                                """
                                INSERT INTO users (email, google_id, is_anonymous, name, picture_url)
                                VALUES (%s, %s, false, %s, %s)
                                RETURNING *
                                """,
                                (user_info['email'], user_info['sub'], user_info['name'], 
                                 user_info['picture'])
                            )
                            
                            # Get free plan
                            free_plan = get_free_subscription_plan(conn)
                            if free_plan:
                                # Create subscription
                                execute_query_single(
                                    conn,
                                    """
                                    INSERT INTO user_subscriptions (
                                        user_id, plan_id, start_date, end_date,
                                        status, is_active
                                    )
                                    VALUES (
                                        %s, %s, CURRENT_TIMESTAMP, 
                                        CURRENT_TIMESTAMP + INTERVAL '100 years',
                                        'active', true
                                    )
                                    """,
                                    (user['id'], free_plan['id'])
                                )
                        
                        conn.commit()
                    except Exception as e:
                        conn.rollback()
                        raise e
                    
                    return user, True
                
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
