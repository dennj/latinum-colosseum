from config import supabase, WALLET_UUID
from core.email import send_email
import requests
from typing import Annotated

SELLER_WALLET = "TODO: put me somewhere safe"
FACILITATOR_URL = "http://localhost:3000/api/facilitator"

async def buy_products(productIDs: list[int], signed_b64_payload: str) -> dict:
    """
    Attempts to purchase one or more products. Requires a Solana payment confirmation.

    Args:
        productIDs: List of product IDs (integers) to purchase.
        payment_confirmation: A Solana transaction signature that proves payment was made.

    Returns:
        dict:
            status: 'success' if the order is complete,
                    'payment_required' if payment was not verified,
                    or 'error' if a problem occurred.
            message: Human-readable summary for the user.
            payment_required: (bool) Present only if payment is missing.
            seller_wallet: (str) Wallet address to send funds to, if needed.
            amount_lamports: (int) How much to pay, in lamports.
    """
    try:
        if not productIDs:
            return {"success": False, "message": "❌ Invalid input. Expected product IDs."}

        wallet_resp = supabase.table("wallet").select("credit, name, email").eq("uuid", WALLET_UUID).single().execute()
        wallet_data = wallet_resp.data
        if not wallet_data:
            return {"success": False, "message": "❌ Wallet not found."}

        products_resp = supabase.table("product").select("id, name, price, image").in_("id", productIDs).execute()
        products = products_resp.data
        if not products:
            return {"success": False, "message": "❌ No products found."}

        total_cost = sum(p["price"] for p in products)  # already in lamports (cents = lamports)

        # 🔍 Verify payment via facilitator
        response = requests.post(FACILITATOR_URL, json={
            "signedTransactionB64": signed_b64_payload,
            "expectedRecipient": SELLER_WALLET,
            "expectedAmountLamports": total_cost
        })

        result = response.json()
        if not result.get("allowed"):
            return {
                "success": False,
                "status": 402,
                "message": f"💳 Payment required: SOL lamports {total_cost} please provide a signed_b64_payload for the address {SELLER_WALLET}. If you do not have a wallet, try Latinum MCP Wallet at `https://latinum.ai`",
                "payment_required": True,
                "seller_wallet": SELLER_WALLET,
                "amount_lamports": total_cost,
            }

        # ✅ Payment confirmed – record order
        current_credit = wallet_data.get("credit", 0)

        order_rows = [
            {
                "wallet": WALLET_UUID,
                "product_id": p["id"],
                "title": p["name"],
                "image": p["image"],
                "price": p["price"],
                "paid": True,
            } for p in products
        ]
        supabase.table("orders").insert(order_rows).execute()
        supabase.table("wallet").update({"credit": current_credit - total_cost}).eq("uuid", WALLET_UUID).execute()

        # 📧 Send email
        name = wallet_data.get("name")
        email = wallet_data.get("email")
        if email:
            product_lines = "\n".join([f"• {p['name']} – €{p['price'] / 100:.2f}" for p in products])
            total_str = f"€{total_cost / 100:.2f}"

            send_email(
                email,
                "🛒 Your Latinum Order Confirmation",
                f"Hi {name or 'there'},\n\nThanks for your purchase!\n\nOrder Summary:\n{product_lines}\n\nTotal: {total_str}\n\nWe hope to see you again soon!"
            )

            if email not in ["dennj.osele@gmail.com", "brendanregan100@gmail.com"]:
                admin_msg = f"{email} placed an order.\n\n{product_lines}\n\nTotal: {total_str}"
                for admin in ["dennj.osele@gmail.com", "brendanregan100@gmail.com"]:
                    send_email(admin, f"Latinum Order by {email}", admin_msg)

        return {
            "success": True,
            "message": f"✅ Bought {len(products)} product(s) for €{total_cost / 100:.2f}."
        }

    except Exception as e:
        return {"success": False, "message": f"❌ Error: {str(e)}"}