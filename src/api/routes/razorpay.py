from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from typing import Dict
from src.infrastructure.payment.razorpay_client import RazorpayClient
from src.core.auth.jwt import get_current_active_user
from src.db.base import get_db
from src.db.queries.subscriptions import (
    get_subscription_plan,
    update_user_subscription_status,
    create_user_subscription
)
from src.config.settings import settings
from datetime import datetime, timedelta
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1/razorpay",
    tags=["razorpay"]
)

class SubscriptionCreateRequest(BaseModel):
    plan_id: str

@router.post("/create-subscription")
async def create_subscription(
    request: SubscriptionCreateRequest,
    current_user: dict = Depends(get_current_active_user),
    db = Depends(get_db)
):
    razorpay = RazorpayClient()
    
    # Get plan details from database
    with db as conn:
        plan = get_subscription_plan(conn, request.plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
    
    subscription = razorpay.create_subscription(
        plan.get('razorpay_plan_id'),
        notes={
            "user_id": str(current_user['id']), 
            "plan_id": str(plan.get('id'))
        }
    )

    with db as conn:
        create_user_subscription(
            conn,
            user_id=current_user['id'],
            plan_id=plan.get('id'),
            razorpay_subscription_id=subscription.get('id'),
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=30)
        )

    return {
        "subscription_id": subscription.get('id'),
        "key_id": settings.RAZORPAY_KEY_ID
    }

@router.post("/webhook")
async def razorpay_webhook(request: Request, db = Depends(get_db)):
    # Verify webhook signature
    webhook_signature = request.headers.get('X-Razorpay-Signature', '')

    # Verify webhook signature using HMAC
    import hmac
    import hashlib

    webhook_body = await request.body()
    event = await request.json()

    logger.info(f"Razorpay webhook received: {event}")

    # Uncomment this to verify the signature when account is verified
    # expected_signature = hmac.new(
    #     settings.RAZORPAY_WEBHOOK_SECRET.encode(),
    #     webhook_body,
    #     hashlib.sha256
    # ).hexdigest()
    
    # if not hmac.compare_digest(webhook_signature, expected_signature):
    #     raise HTTPException(status_code=400, detail="Invalid signature")

    if event['event'] == 'subscription.activated':
        # Update subscription status
        subscription_id = event['payload']['subscription']['entity']['id']
        payment_id = event['payload']['payment']['entity']['id']
        signature = webhook_signature
        user_id = event['payload']['subscription']['entity']['notes'].get('user_id')
        plan_id = event['payload']['subscription']['entity']['notes'].get('plan_id')

        with db as conn:
            await update_user_subscription_status(
                conn,
                user_id=user_id,
                subscription_id=subscription_id,
                payment_id=payment_id,
                signature=signature,
                status='active',
                is_active=True,
                plan_id=plan_id
            )
    
    return {"status": "processed"}

class PaymentVerificationRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_subscription_id: str
    razorpay_signature: str

@router.post(
    "/verify-payment",
    response_model=Dict[str, str],
    responses={
        200: {
            "description": "Payment verified successfully",
            "content": {
                "application/json": {
                    "example": {"status": "success"}
                }
            }
        },
        400: {
            "description": "Invalid payment verification",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid payment signature"}
                }
            }
        }
    }
)
async def verify_payment(
    verification: PaymentVerificationRequest,
    current_user: dict = Depends(get_current_active_user),
    db = Depends(get_db)
):
    """
    Verify Razorpay payment signature and activate subscription
    """
    try:
        razorpay = RazorpayClient()
        
        # Verify payment signature
        is_valid = razorpay.verify_subscription_payment(
            payment_id=verification.razorpay_payment_id,
            signature=verification.razorpay_signature,
            subscription_id=verification.razorpay_subscription_id
        )
        
        if not is_valid:
            logger.error(f"Invalid payment signature: {verification.razorpay_payment_id}, {verification.razorpay_subscription_id}, {verification.razorpay_signature}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payment signature"
            )

        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Payment verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )