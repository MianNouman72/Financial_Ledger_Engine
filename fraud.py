class FraudDetector:
    def __init__(self):
        # Rules configuration or threshold values can be set here
        self.max_withdrawal_threshold = 10000.0

    def evaluate(self, event: dict, account_history: list) -> bool:
        """
        Evaluates an event against pluggable fraud detection rules.
        Returns True if fraud/suspicious activity is detected, otherwise False.
        """
        event_type = event.get("type")
        amount = event.get("amount", 0.0)

        # Rule 1: High single transaction amount
        if event_type in ["WITHDRAW", "TRANSFER"] and amount > self.max_withdrawal_threshold:
            return True

        # Rule 2: Rapid successive withdrawals check
        if event_type == "WITHDRAW" and len(account_history) >= 3:
            # Check if last 3 transactions were also withdrawals within a short window
            recent_types = [tx.get("type") for tx in account_history[-3:]]
            if all(t == "WITHDRAW" for t in recent_types):
                return True

        return False