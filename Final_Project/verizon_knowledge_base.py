"""verizon_knowledge_base.py — authoritative Verizon policy documentation

These are simplified policy snippets representing actual Verizon terms.
Real implementation would pull from official Verizon docs.
"""

VERIZON_LEGAL_DOCS = {
    "billing_and_charges": """
    BILLING AND CHARGES POLICY
    
    Your Verizon bill includes monthly service charges, device payments (if applicable),
    taxes, and regulatory fees. Monthly charges are based on your service plan.
    
    Late fees: A late fee of up to $5 may be applied if payment is more than 20 days late.
    This is not a penalty but a reasonable estimate of Verizon's costs.
    
    Taxes and regulatory fees vary by location and are added to your bill. These fees
    are mandated by federal, state, and local governments.
    
    Paper bill fee: A $1.25 monthly fee applies if you request a paper bill.
    
    Premium services (international calling plans, extra data, etc.) are charged
    based on your selections and appear as line items on your bill.
    
    You have the right to dispute any charge within 60 days of the billing date.
    """,
    
    "cancellation_and_termination": """
    EARLY TERMINATION AND CANCELLATION POLICY
    
    Cancellation by customer: You may cancel your service at any time. If you cancel
    before your contract ends, an early termination fee (ETF) of up to $350 per line
    may apply, depending on the phone you're paying off.
    
    The ETF decreases over time. Generally, the fee is calculated as follows:
    - Months 1-6: Full amount
    - Months 7-12: 50% of the original ETF
    - Month 13+: $0 ETF
    
    Device payment plans: If you're on a device payment plan, you may pay off your phone
    early without penalty. The remaining device balance becomes due upon cancellation.
    
    Service obligations: If you cancel, you remain responsible for charges through the
    cancellation date, including prorated monthly charges.
    
    Cancellation can be processed online, via phone, or at a Verizon store.
    """,
    
    "data_limits_and_throttling": """
    DATA LIMITS AND SPEED THROTTLING POLICY
    
    Data allowances vary by plan. Once you reach your monthly data limit, your speeds
    may be reduced. This is called "throttling."
    
    Throttling speeds: After exceeding your data limit, speeds are typically reduced to
    approximately 128 kbps (on 4G LTE). This allows basic web browsing and email but
    may not support video streaming or large downloads.
    
    Duration: Throttling remains in effect until the end of your billing cycle. Your
    normal speeds resume on the first day of the next billing period.
    
    Avoiding throttling:
    - Monitor your data usage through the My Verizon app
    - Add extra data before reaching your limit (additional charges apply)
    - Upgrade to an unlimited data plan
    
    Unlimited plans: Verizon offers unlimited data plans that do not have speed reductions
    based on data caps. These plans may have other limitations (see plan details).
    """,
    
    "international_roaming_travelpass": """
    INTERNATIONAL ROAMING AND TRAVELPASS POLICY
    
    When traveling internationally, your phone can access local networks, but charges may apply.
    
    Standard international rates: Without a plan, international usage is charged per-minute
    for calls, per-text for SMS, and per-megabyte for data. Rates vary by country.
    
    TravelPass: Verizon offers TravelPass, which charges a daily fee (typically $10/day)
    when you use data, calls, or texts while abroad. No charge for days you don't use
    your phone. This provides unlimited usage within a single country.
    
    International monthly plans: You can purchase monthly data and calling plans for
    specific countries or regions at discounted rates.
    
    Activation: TravelPass and international plans activate automatically when you use
    your phone abroad, unless you disable them in your account settings.
    
    Destination-specific: Rates and available plans vary significantly by country.
    Check the My Verizon app before traveling for the most current rates.
    """,
    
    "device_payment_plans": """
    DEVICE PAYMENT PLANS POLICY
    
    Verizon allows customers to pay for devices in monthly installments instead of
    paying the full price upfront.
    
    Monthly payments: Device payments are divided equally over 24 or 36 months (depending
    on the device and promotion). Payments are added to your monthly bill.
    
    Early payoff: You may pay off the remaining balance on your device at any time without
    penalty. You simply pay the remaining installments in full.
    
    Device trade-in: If you trade in your device before payments are complete, Verizon
    credits the trade-in value toward the remaining balance.
    
    Upgrading: When you upgrade to a new device with a new payment plan, the old device
    plan is settled (either through trade-in credit or you pay the remaining balance).
    
    Insurance and protection: Device insurance (Verizon Protection Plan) is optional and
    covers accidental damage, theft, and loss for an additional monthly fee.
    
    Ownership: You own the device once you finish paying for it. During payment, you own
    the device but have a payment obligation to Verizon.
    """,
    
    "dispute_resolution_arbitration": """
    DISPUTE RESOLUTION AND ARBITRATION POLICY
    
    Billing disputes: If you believe your bill is incorrect, you must notify Verizon
    within 60 days of the billing date. Provide a written explanation of the disputed charge.
    
    Investigation process: Verizon will investigate your dispute. This process typically
    takes 30-60 days. During investigation, the disputed amount may be credited provisionally.
    
    Resolution: Once the investigation concludes, Verizon will either:
    1. Confirm the charge and remove any provisional credit, or
    2. Adjust your bill and keep the credit
    
    Arbitration: Rather than filing a lawsuit, most disputes are resolved through binding
    arbitration or small claims court. You retain the right to pursue claims individually
    (not as part of a class action).
    
    Arbitration process: Disputes are heard by a neutral arbitrator who issues a binding
    decision. This is typically faster and less expensive than litigation.
    
    Opting out: You may opt out of arbitration by sending written notice to Verizon within
    30 days of this notice. After opting out, disputes may be resolved in court.
    """,
}
