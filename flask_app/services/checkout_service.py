"""Checkout pricing, validation, inventory locks, and order creation."""

from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timedelta

from flask import current_app, session
from flask_login import current_user

from ..extensions import db
from ..models import (
    CheckoutAbandonment,
    CheckoutInventoryLock,
    Coupon,
    LoyaltyWallet,
    Order,
    OrderItem,
    Payment,
    Product,
    UserAddress,
)
from ..shop_state import get_cart_payload, remove_from_cart

PINCODE_PATTERN = re.compile(r"^\d{6}$")

SHIPPING_METHODS = {
    "standard": {
        "id": "standard",
        "label": "Standard Delivery",
        "fee": 0.0,
        "etaDays": 5,
        "badge": "Best value",
    },
    "express": {
        "id": "express",
        "label": "Express Delivery",
        "fee": 99.0,
        "etaDays": 2,
        "badge": "Fast",
    },
    "same_day": {
        "id": "same_day",
        "label": "Same Day Delivery",
        "fee": 199.0,
        "etaDays": 0,
        "badge": "Today",
    },
}


def _round_money(value: float) -> float:
    return round(float(value or 0), 2)


def get_checkout_lock_token() -> str:
    token = session.get("checkout_lock_token")
    if not token:
        token = secrets.token_urlsafe(24)
        session["checkout_lock_token"] = token
        session.modified = True
    return token


def get_guest_checkout_token() -> str:
    token = session.get("guest_checkout_token")
    if not token:
        token = secrets.token_urlsafe(16)
        session["guest_checkout_token"] = token
        session.modified = True
    return token


def get_or_create_wallet(user_id: int) -> LoyaltyWallet:
    wallet = LoyaltyWallet.query.filter_by(user_id=user_id).first()
    if wallet:
        return wallet
    default_coins = int(current_app.config.get("DEFAULT_SIGNUP_COINS", 250))
    wallet = LoyaltyWallet(user_id=user_id, balance_coins=default_coins)
    db.session.add(wallet)
    db.session.commit()
    return wallet


def validate_cart_stock(cart_items: list[dict]) -> dict | None:
    if not cart_items:
        return {"error": "Your cart is empty."}
    for item in cart_items:
        product = db.session.get(Product, item.get("id"))
        if not product or not product.active:
            return {"error": f"{item.get('name', 'Item')} is no longer available."}
        qty = int(item.get("quantity") or 0)
        if qty <= 0:
            return {"error": "Invalid quantity in cart."}
        if product.stock_quantity < qty:
            return {
                "error": f"Only {product.stock_quantity} units left for {product.name}.",
            }
    return None


def refresh_inventory_locks(cart_items: list[dict], lock_token: str | None = None) -> None:
    lock_token = lock_token or get_checkout_lock_token()
    expires = datetime.utcnow() + timedelta(
        minutes=int(current_app.config.get("CHECKOUT_LOCK_MINUTES", 15))
    )
    CheckoutInventoryLock.query.filter_by(lock_token=lock_token).delete()
    for item in cart_items:
        db.session.add(
            CheckoutInventoryLock(
                product_id=int(item["id"]),
                quantity=int(item["quantity"]),
                lock_token=lock_token,
                expires_at=expires,
            )
        )
    db.session.commit()


def _locked_quantity_for_product(product_id: int, exclude_token: str | None = None) -> int:
    now = datetime.utcnow()
    query = CheckoutInventoryLock.query.filter(
        CheckoutInventoryLock.product_id == product_id,
        CheckoutInventoryLock.expires_at > now,
    )
    if exclude_token:
        query = query.filter(CheckoutInventoryLock.lock_token != exclude_token)
    return sum(row.quantity for row in query.all())


def validate_inventory_locks(cart_items: list[dict], lock_token: str) -> dict | None:
    for item in cart_items:
        product = db.session.get(Product, item["id"])
        if not product:
            continue
        other_locked = _locked_quantity_for_product(product.id, exclude_token=lock_token)
        available = product.stock_quantity - other_locked
        if int(item["quantity"]) > available:
            return {
                "error": f"{product.name} stock is reserved by another checkout. Try again shortly.",
            }
    return None


def find_coupon(code: str) -> Coupon | None:
    normalized = (code or "").strip().upper()
    if not normalized:
        return None
    return Coupon.query.filter_by(code=normalized).first()


def validate_coupon(coupon: Coupon | None, order_amount: float) -> dict | None:
    if not coupon:
        return {"error": "Invalid coupon code."}
    if getattr(coupon, "is_draft", False):
        return {"error": "This coupon is not available."}
    if not coupon.active:
        return {"error": "This coupon is no longer active."}
    if getattr(coupon, "starts_at", None) and coupon.starts_at > datetime.utcnow():
        return {"error": "This coupon is not active yet."}
    if coupon.expires_at and coupon.expires_at < datetime.utcnow():
        return {"error": "This coupon has expired."}
    if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
        return {"error": "This coupon has reached its usage limit."}
    if order_amount < float(coupon.min_order_amount or 0):
        return {
            "error": f"Minimum order amount is ₹{int(coupon.min_order_amount)} for this coupon.",
        }
    return None


def coupon_discount_amount(coupon: Coupon, eligible_amount: float) -> float:
    eligible_amount = max(float(eligible_amount or 0), 0.0)
    dtype = coupon.discount_type or "percent"
    if dtype == "free_shipping":
        return 0.0
    if dtype == "fixed":
        discount = float(coupon.discount_value or 0)
    elif dtype == "buy_x_get_y":
        discount = float(coupon.discount_value or 0)
    else:
        discount = eligible_amount * (float(coupon.discount_value or 0) / 100.0)
    if coupon.max_discount is not None:
        discount = min(discount, float(coupon.max_discount))
    return _round_money(min(discount, eligible_amount))


def max_redeemable_coins(wallet_balance: int, payable_before_coins: float) -> int:
    coin_value = float(current_app.config.get("COIN_VALUE_INR", 1))
    max_percent = float(current_app.config.get("MAX_COIN_REDEEM_PERCENT", 20)) / 100.0
    if coin_value <= 0:
        return 0
    cap_by_order = int(payable_before_coins * max_percent / coin_value)
    return max(0, min(int(wallet_balance), cap_by_order))


def calculate_totals(
    cart_items: list[dict],
    *,
    shipping_method: str = "standard",
    coupon: Coupon | None = None,
    coins_to_redeem: int = 0,
    wallet_balance: int = 0,
) -> dict:
    subtotal = _round_money(sum(float(i.get("mrpTotal") or 0) for i in cart_items))
    product_discount = _round_money(sum(float(i.get("discountTotal") or 0) for i in cart_items))
    gst_total = _round_money(sum(float(i.get("gstTotal") or 0) for i in cart_items))
    base_shipping = _round_money(sum(float(i.get("shippingTotal") or 0) for i in cart_items))

    method = SHIPPING_METHODS.get(shipping_method, SHIPPING_METHODS["standard"])
    method_fee = float(method["fee"])
    shipping_charges = _round_money(base_shipping + method_fee)

    items_payable = _round_money(
        sum(float(i.get("lineTotal") or 0) for i in cart_items) + shipping_charges
    )
    coupon_discount = 0.0
    if coupon:
        coupon_discount = coupon_discount_amount(coupon, items_payable)

    after_coupon = _round_money(max(items_payable - coupon_discount, 0))
    platform_fee = _round_money(float(current_app.config.get("CHECKOUT_PLATFORM_FEE", 0)))
    payable_before_coins = _round_money(after_coupon + platform_fee)

    max_coins = max_redeemable_coins(wallet_balance, payable_before_coins)
    coins_to_redeem = max(0, min(int(coins_to_redeem), max_coins))
    coin_value = float(current_app.config.get("COIN_VALUE_INR", 1))
    coin_discount = _round_money(coins_to_redeem * coin_value)

    grand_total = _round_money(max(payable_before_coins - coin_discount, 0))

    return {
        "subtotal": subtotal,
        "productDiscount": product_discount,
        "couponDiscount": coupon_discount,
        "coinDiscount": coin_discount,
        "coinsRedeemed": coins_to_redeem,
        "maxRedeemableCoins": max_coins,
        "availableCoins": wallet_balance,
        "coinValueInr": coin_value,
        "gstTotal": gst_total,
        "shippingCharges": shipping_charges,
        "shippingMethodFee": method_fee,
        "platformFee": platform_fee,
        "grandTotal": grand_total,
        "itemCount": sum(int(i.get("quantity") or 0) for i in cart_items),
        "shippingMethod": method,
    }


def track_abandonment(step: str, email: str | None = None, cart_items: list | None = None) -> None:
    snapshot = json.dumps(cart_items or [])
    user_id = current_user.id if current_user.is_authenticated else None
    guest_token = None if user_id else get_guest_checkout_token()
    query = CheckoutAbandonment.query
    if user_id:
        row = query.filter_by(user_id=user_id).order_by(CheckoutAbandonment.updated_at.desc()).first()
    else:
        row = query.filter_by(guest_token=guest_token).order_by(CheckoutAbandonment.updated_at.desc()).first()
    if not row:
        row = CheckoutAbandonment(user_id=user_id, guest_token=guest_token)
        db.session.add(row)
    row.last_step = step
    row.email = email or row.email
    row.cart_snapshot = snapshot
    row.updated_at = datetime.utcnow()
    db.session.commit()


def address_to_shipping_dict(address: dict) -> dict:
    return {
        "shipping_full_name": address.get("fullName") or address.get("full_name"),
        "shipping_mobile": address.get("mobile"),
        "shipping_house": address.get("house"),
        "shipping_street": address.get("street"),
        "shipping_landmark": address.get("landmark"),
        "shipping_city": address.get("city"),
        "shipping_state": address.get("state"),
        "shipping_pincode": re.sub(r"\s+", "", address.get("pincode") or ""),
        "shipping_country": address.get("country") or "India",
    }


def validate_address_payload(data: dict) -> dict | None:
    required = ["fullName", "mobile", "house", "street", "city", "state", "pincode"]
    for field in required:
        if not str(data.get(field) or "").strip():
            return {"error": f"Missing required field: {field}"}
    pincode = re.sub(r"\s+", "", str(data.get("pincode") or ""))
    if not PINCODE_PATTERN.match(pincode):
        return {"error": "Enter a valid 6-digit PIN code."}
    mobile = re.sub(r"\s+", "", str(data.get("mobile") or ""))
    if len(mobile) < 10:
        return {"error": "Enter a valid mobile number."}
    return None


def generate_order_number() -> str:
    return f"UC{datetime.utcnow().strftime('%y%m%d%H%M%S')}{secrets.token_hex(2).upper()}"


def place_order(
    *,
    contact: dict,
    address: dict,
    shipping_method: str,
    payment_method: str,
    coupon_code: str | None,
    coins_to_redeem: int,
    estimated_delivery: str | None,
    payment_meta: dict | None = None,
) -> dict:
    user = current_user
    cart_payload = get_cart_payload(user=user)
    cart_items = cart_payload["items"]
    stock_error = validate_cart_stock(cart_items)
    if stock_error:
        return stock_error

    lock_token = get_checkout_lock_token()
    lock_error = validate_inventory_locks(cart_items, lock_token)
    if lock_error:
        return lock_error

    addr_error = validate_address_payload(address)
    if addr_error:
        return addr_error

    wallet_balance = 0
    if user.is_authenticated:
        wallet = get_or_create_wallet(user.id)
        wallet_balance = int(wallet.balance_coins or 0)

    coupon = find_coupon(coupon_code) if coupon_code else None
    if coupon_code and not coupon:
        return {"error": "Invalid coupon code."}
    if coupon:
        prelim = calculate_totals(cart_items, shipping_method=shipping_method, coupon=None)
        coupon_error = validate_coupon(coupon, prelim["grandTotal"])
        if coupon_error:
            return coupon_error

    totals = calculate_totals(
        cart_items,
        shipping_method=shipping_method,
        coupon=coupon,
        coins_to_redeem=coins_to_redeem,
        wallet_balance=wallet_balance,
    )

    shipping_fields = address_to_shipping_dict(address)
    order = Order(
        order_number=generate_order_number(),
        user_id=user.id if user.is_authenticated else None,
        guest_token=None if user.is_authenticated else get_guest_checkout_token(),
        contact_name=contact.get("fullName", "").strip(),
        contact_email=contact.get("email", "").strip().lower(),
        contact_phone=re.sub(r"\s+", "", contact.get("mobile", "")),
        shipping_method=shipping_method,
        shipping_charge=totals["shippingCharges"],
        estimated_delivery=estimated_delivery,
        subtotal=totals["subtotal"],
        product_discount=totals["productDiscount"],
        coupon_code=coupon.code if coupon else None,
        coupon_discount=totals["couponDiscount"],
        coins_redeemed=totals["coinsRedeemed"],
        coin_discount=totals["coinDiscount"],
        gst_total=totals["gstTotal"],
        platform_fee=totals["platformFee"],
        grand_total=totals["grandTotal"],
        status="confirmed",
        payment_method=payment_method,
        payment_status="paid" if payment_method != "cod" else "pending",
        **shipping_fields,
    )
    db.session.add(order)
    db.session.flush()

    for item in cart_items:
        product = db.session.get(Product, item["id"])
        if not product:
            db.session.rollback()
            return {"error": "A product in your cart is unavailable."}
        qty = int(item["quantity"])
        if product.stock_quantity < qty:
            db.session.rollback()
            return {"error": f"Insufficient stock for {product.name}."}
        product.stock_quantity -= qty
        db.session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=item.get("name") or product.name,
                product_sku=item.get("sku"),
                variant=item.get("category"),
                quantity=qty,
                unit_price=float(item.get("discountPrice") or 0),
                line_total=_round_money(float(item.get("lineTotal") or 0)),
                image_url=item.get("imageUrl"),
            )
        )
        remove_from_cart(product.id, user=user)

    if coupon:
        coupon.used_count = int(coupon.used_count or 0) + 1

    if user.is_authenticated and totals["coinsRedeemed"] > 0:
        wallet = get_or_create_wallet(user.id)
        wallet.balance_coins = max(0, int(wallet.balance_coins) - totals["coinsRedeemed"])

    txn_id = f"TXN{secrets.token_hex(6).upper()}"
    payment_status = "paid" if payment_method != "cod" else "pending"
    db.session.add(
        Payment(
            order_id=order.id,
            method=payment_method,
            status=payment_status,
            amount=totals["grandTotal"],
            transaction_id=txn_id,
            metadata_json=json.dumps(payment_meta or {}),
        )
    )

    CheckoutInventoryLock.query.filter_by(lock_token=lock_token).delete()
    session.pop("checkout_lock_token", None)
    db.session.commit()

    return {
        "ok": True,
        "order": order.to_dict(),
        "redirect": f"/shop/checkout/success/{order.order_number}",
    }


def seed_default_coupons() -> None:
    defaults = [
        ("WELCOME10", "percent", 10, 499, 500, "10% off orders above ₹499"),
        ("FLAT200", "fixed", 200, 1499, None, "₹200 off orders above ₹1499"),
        ("URBAN50", "fixed", 50, 299, None, "₹50 off orders above ₹299"),
    ]
    for code, dtype, value, minimum, max_disc, desc in defaults:
        if Coupon.query.filter_by(code=code).first():
            continue
        db.session.add(
            Coupon(
                name=code,
                code=code,
                description=desc,
                discount_type=dtype,
                discount_value=value,
                min_order_amount=minimum,
                max_discount=max_disc,
                active=True,
                is_draft=False,
            )
        )
    db.session.commit()
