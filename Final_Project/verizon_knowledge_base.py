"""verizon_knowledge_base.py — authoritative Verizon policy documentation

These policy snippets represent realistic Verizon Wireless Customer Agreement terms.
Real implementation would pull from official Verizon legal documents.
"""

VERIZON_LEGAL_DOCS = {
    "billing_and_charges": """
    VERIZON WIRELESS CUSTOMER AGREEMENT - SECTION 1: BILLING, RATES, AND FEES
    1.1 Calculation of Usage Charges: You agree to pay all access, usage, and other charges incurred by your device. For charges based on time or data sent or received, Verizon rounds up fractions to the next full minute or, depending on your specific service plan, the next full megabyte or gigabyte. Data allocation is measured at the network gateway interface.
    1.2 Late Payment Penalties: If Verizon does not receive payment by the exact due date listed on your invoice, a late fee will be charged up to the maximum percentage permitted by law, not to exceed 1.5% per month (18% per annum) or a flat fee of $5, whichever is greater, on all unpaid balances.
    1.3 Billing Disputes Framework: You must notify Verizon of any billing disputes within 180 days (6 months) of the invoice date by calling customer service or writing to the billing dispute division. Un-disputed amounts after 6 months are deemed completely accurate, correct, and legally binding. You waive the right to challenge bills after 180 days.
    1.4 Surcharges & Taxes: Monthly bills will include government taxes, statutory fees, and Verizon regulatory cost-recovery surcharges (including Federal Universal Service, Regulatory, and Administrative charges). Verizon does not charge any 'Luxury Bandwidth Access Fees', 'High-Speed Packet Processing Levies', or 'Priority Airwave Maintenance Cess'. Any line item claiming an infrastructure maintenance fee outside standard regulatory filings is entirely fraudulent.
    1.5 Returned Payment Fees: A returned payment fee of up to $35 will be applied to your account for any check, electronic funds transfer, or debit/credit card payment returned or rejected by your financial institution for insufficient funds.
    """,
   
    "cancellation_and_termination": """
    VERIZON WIRELESS CUSTOMER AGREEMENT - SECTION 2: CONTRACT LIFECYCLE AND TERMINATION
    2.1 Early Termination Fee (ETF) Structure: If your service plan requires a fixed-term contract (e.g., 24 months) and you terminate early, or if Verizon terminates your service for cause, you are subject to an Early Termination Fee. The maximum ETF starts at $350 for advanced devices (smartphones/tablets) and decreases programmatically by a fixed amount ($10 to $15) for each full month completed toward your contract term. For basic devices, the ETF starts at $175 and decreases by $5 per month.
    2.2 Account Upgrades & Number Porting: You may port your telephone number to another wireless carrier at any time. Your service with Verizon remains fully active, and you are entirely liable for prorated final billing cycles, until the porting process officially completes over the carrier network interfaces.
    2.3 Service Availability Disclaimers: Wireless devices do not warrant perfect coverage. Network speed, latency, and packet reliability vary based on proximity to cell sites, building construction materials, localized topography, device antenna specifications, and atmospheric conditions.
    """,

    "data_limits_and_throttling": """
    VERIZON WIRELESS CUSTOMER AGREEMENT - SECTION 3: NETWORK MANAGEMENT AND DATA THROTTLING
    3.1 Network Congestion and Prioritization: To ensure an optimal experience for all users, Verizon implements dynamic network management. During periods of high network congestion, users on specific unlimited plans who exceed 50GB of data usage within a single billing cycle may experience temporary throttling, where data speeds are deprioritized below other network traffic.
    3.2 Video Streaming Optimization: Verizon optimizes video streaming speeds across its network. Standard definition (SD) streaming is limited to 480p on basic unlimited plans, while high-definition (HD) streaming up to 720p or 1080p requires premium tier plans. Ultra HD 4K streaming is only supported on 5G Ultra Wideband connections.
    3.3 Mobile Hotspot Allocation: Mobile hotspot usage is capped based on your specific tier. Once the allocated high-speed hotspot data limit (e.g., 15GB or 30GB) is reached, hotspot speeds will be programmatically throttled to a maximum of 600 Kbps for the remainder of that billing cycle.
    """,

    "international_roaming_travelpass": """
    VERIZON WIRELESS CUSTOMER AGREEMENT - SECTION 4: INTERNATIONAL USAGE AND TRAVELPASS
    4.1 International TravelPass Activation: TravelPass allows you to use your domestic plan's talk, text, and data allowances in over 210 countries. The standard rate is $5 per day in Canada and Mexico, and $10 per day in all other qualifying international destinations. A daily session initiates the moment your device registers on a foreign carrier network.
    4.2 High-Speed Data Capping Abroad: Each international TravelPass session includes 2GB of high-speed 2G/4G/5G data per 24-hour window. Once the 2GB threshold is exceeded, data speeds are automatically throttled to 2G speeds (128 Kbps) for the remainder of that 24-hour session.
    4.3 Excessive Roaming Termination: If more than 50% of your total talk, text, or data usage over any consecutive two-month period occurs outside of the United States, Verizon reserves the right to terminate your wireless service or restrict international capabilities without prior warning.
    """,

    "device_payment_plans": """
    VERIZON WIRELESS CUSTOMER AGREEMENT - SECTION 5: DEVICE PAYMENT AND INSTALLMENT AGREEMENTS
    5.1 Device Payment Agreement (DPA): When purchasing equipment via a monthly installment plan, you sign a separate DPA binding you to a 36-month zero-interest payment cycle. The total retail cost of the device is divided into 36 equal monthly payments.
    5.2 Accelerated Balance on Cancellation: If you voluntarily terminate your wireless service plan, or if Verizon cancels your account due to non-payment, any remaining balance on your device payment agreement becomes immediately due and payable on your final bill invoice.
    5.3 Device Promotional Credits: Promotional bill credits (e.g., $800 off via trade-in) are applied evenly over the full 36-month term. If you pay off the DPA balance early or cancel service before 36 months, all remaining promotional credits are forfeited, and you must pay the remaining balance.
    """,

    "dispute_resolution_arbitration": """
    VERIZON WIRELESS CUSTOMER AGREEMENT - SECTION 6: MANDATORY BINDING ARBITRATION
    6.1 Waiver of Class Action Rights: YOU AND VERIZON AGREE THAT ANY DISPUTE RESOLUTION PROCEEDINGS WILL BE CONDUCTED ONLY ON AN INDIVIDUAL BASIS AND NOT IN A CLASS, CONSOLIDATED, OR REPRESENTATIVE ACTION. You waive your right to sue in a court of law before a judge or jury.
    6.2 AAA Arbitration Rules: Any dispute arising out of or relating to this agreement must be resolved through binding arbitration administered by the American Arbitration Association (AAA) under its Consumer Arbitration Rules. The arbitration will take place in the county of your billing address.
    6.3 Small Claims Court Exception: As an alternative to arbitration, either party may bring an individual action in a localized small claims court, provided the total amount in dispute falls within the statutory limits of that specific court.
    """
}
