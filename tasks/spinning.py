import random
from decimal import Decimal

def spin_wheel(user_profile):
    """
    Determines the outcome of a spin based on the user's plan and balance.
    
    - Base outcomes: $0.00, $0.10, $0.20.
    - If the user is eligible (Plan 10 or Plan 50), a $2.00 outcome is added.
    - If the user's balance is greater than $1.8, there is a 90% chance to force a loss ($0.00).
    """
    # Base outcomes and corresponding weights
    base_outcomes = [Decimal("0.00"), Decimal("0.10"), Decimal("0.20")]
    base_weights = [0.4, 0.3, 0.2]  # Total = 0.9

    # If user is eligible, add the $2.00 reward outcome.
    if user_profile.plan and user_profile.plan.name.lower() in ['plan 10', 'plan 50']:
        base_outcomes.append(Decimal("2.00"))
        base_weights.append(0.1)  # Now total = 1.0

    # If the user's balance is over $1.8, force a loss 90% of the time.
    if user_profile.balance > Decimal("1.8"):
        # Prepend a forced loss outcome with weight 0.9.
        outcomes = [Decimal("0.00")] + base_outcomes
        # Scale the base weights so that they sum to 0.1.
        total_base = sum(base_weights)
        scaled_weights = [w * (0.1 / total_base) for w in base_weights]
        probabilities = [0.9] + scaled_weights
    else:
        outcomes = base_outcomes
        probabilities = base_weights

    # Ensure both lists have the same length.
    if len(outcomes) != len(probabilities):
        raise ValueError("Outcomes and probabilities lists do not match in length!")

    reward = random.choices(outcomes, weights=probabilities, k=1)[0]
    return reward
