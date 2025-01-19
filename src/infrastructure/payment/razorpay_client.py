import razorpay
from src.config.settings import settings

class RazorpayClient:
    def __init__(self):
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

    def create_subscription(self, plan_id: str, total_count: int = 1, notes: dict = None):
        try:
            subscription_data = {
                "plan_id": plan_id,
                "total_count": total_count,  # Number of billing cycles
                "customer_notify": 1  # Notify customer about payments
            }

            if notes:
                subscription_data['notes'] = notes

            subscription = self.client.subscription.create(subscription_data)
            return subscription
        except Exception as e:
            raise Exception(f"Failed to create subscription: {str(e)}")

    def verify_subscription_payment(self, payment_id: str, signature: str, subscription_id: str):
        try:
            return self.client.utility.verify_payment_signature({
                'razorpay_signature': signature,
                'razorpay_payment_id': payment_id,
                'razorpay_subscription_id': subscription_id
            })
        except Exception:
            return False