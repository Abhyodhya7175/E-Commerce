from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Product, UserAddress
from ..routes.commerce import _cart_recommendations
from ..services.checkout_service import (
    SHIPPING_METHODS,
    calculate_totals,
    find_coupon,
    get_checkout_lock_token,
    get_or_create_wallet,
    place_order,
    refresh_inventory_locks,
    seed_default_coupons,
    track_abandonment,
    validate_address_payload,
    validate_cart_stock,
    validate_coupon,
)
from ..shop_state import get_cart_payload, validate_csrf_token

checkout_bp = Blueprint("checkout", __name__)


def _json_error(message: str, status: int = 400):
    return jsonify(success=False, error=message), status


def _require_csrf():
    if not validate_csrf_token():
        return _json_error("Invalid or missing CSRF token.", 403)
    return None


@checkout_bp.route("/checkout")
def checkout_page():
    payload = get_cart_payload()
    if not payload["items"]:
        return redirect(url_for("commerce.cart_page"))
    recommendations = _cart_recommendations(payload["items"], limit=8)
    user = current_user if current_user.is_authenticated else None
    addresses = []
    wallet = {"balanceCoins": 0, "coinValueInr": 1}
    contact = {"fullName": "", "email": "", "mobile": ""}
    from flask import current_app

    if user:
        addresses = [
            a.to_dict()
            for a in UserAddress.query.filter_by(user_id=user.id)
            .order_by(UserAddress.is_default.desc(), UserAddress.id.desc())
        ]
        w = get_or_create_wallet(user.id)
        wallet = {"balanceCoins": int(w.balance_coins or 0)}
        contact = {
            "fullName": user.name or "",
            "email": user.email or "",
            "mobile": "",
        }
    wallet["coinValueInr"] = float(current_app.config.get("COIN_VALUE_INR", 1))
    refresh_inventory_locks(payload["items"])
    return render_template(
        "shop/checkout.html",
        cart_payload=payload,
        recommended_products=recommendations,
        addresses=addresses,
        contact=contact,
        wallet=wallet,
        shipping_methods=list(SHIPPING_METHODS.values()),
        is_logged_in=user is not None,
    )


@checkout_bp.route("/checkout/success/<order_number>")
def checkout_success(order_number: str):
    from ..models import Order
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    return render_template("shop/checkout_success.html", order=order)


@checkout_bp.route("/api/checkout/bootstrap", methods=["GET"])
def checkout_bootstrap():
    payload = get_cart_payload()
    user = current_user if current_user.is_authenticated else None
    addresses = []
    wallet = {"balanceCoins": 0}
    if user.is_authenticated:
        addresses = [a.to_dict() for a in UserAddress.query.filter_by(user_id=user.id).order_by(UserAddress.is_default.desc())]
        wallet = {"balanceCoins": int(get_or_create_wallet(user.id).balance_coins or 0)}
    return jsonify(
        success=True,
        cart=payload,
        addresses=addresses,
        wallet=wallet,
        shippingMethods=list(SHIPPING_METHODS.values()),
        lockToken=get_checkout_lock_token(),
        isLoggedIn=user.is_authenticated,
    )


@checkout_bp.route("/api/checkout/preview", methods=["POST"])
def checkout_preview():
    csrf = _require_csrf()
    if csrf:
        return csrf
    data = request.get_json(silent=True) or {}
    payload = get_cart_payload()
    items = payload["items"]
    stock_error = validate_cart_stock(items)
    if stock_error:
        return _json_error(stock_error["error"])

    shipping_method = (data.get("shippingMethod") or "standard").strip()
    coupon_code = (data.get("couponCode") or "").strip()
    coins = int(data.get("coinsToRedeem") or 0)
    coupon = find_coupon(coupon_code) if coupon_code else None
    if coupon_code and not coupon:
        return _json_error("Invalid coupon code.")

    wallet_balance = 0
    if current_user.is_authenticated:
        wallet_balance = int(get_or_create_wallet(current_user.id).balance_coins or 0)

    if coupon:
        prelim = calculate_totals(items, shipping_method=shipping_method)
        err = validate_coupon(coupon, prelim["grandTotal"])
        if err:
            return _json_error(err["error"])

    totals = calculate_totals(
        items,
        shipping_method=shipping_method,
        coupon=coupon,
        coins_to_redeem=coins,
        wallet_balance=wallet_balance,
    )
    refresh_inventory_locks(items)
    return jsonify(success=True, totals=totals, cart=payload, appliedCoupon=coupon.to_dict() if coupon else None)


@checkout_bp.route("/api/checkout/apply-coupon", methods=["POST"])
def apply_coupon():
    csrf = _require_csrf()
    if csrf:
        return csrf
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip()
    shipping_method = (data.get("shippingMethod") or "standard").strip()
    coins = int(data.get("coinsToRedeem") or 0)
    coupon = find_coupon(code)
    if not coupon:
        return _json_error("Invalid coupon code.")
    payload = get_cart_payload()
    wallet_balance = 0
    if current_user.is_authenticated:
        wallet_balance = int(get_or_create_wallet(current_user.id).balance_coins or 0)
    prelim = calculate_totals(
        payload["items"],
        shipping_method=shipping_method,
        coupon=None,
        coins_to_redeem=coins,
        wallet_balance=wallet_balance,
    )
    err = validate_coupon(coupon, prelim["grandTotal"] + prelim.get("coinDiscount", 0))
    if err:
        return _json_error(err["error"])
    wallet_balance = 0
    if current_user.is_authenticated:
        wallet_balance = int(get_or_create_wallet(current_user.id).balance_coins or 0)
    totals = calculate_totals(
        payload["items"],
        shipping_method=shipping_method,
        coupon=coupon,
        coins_to_redeem=coins,
        wallet_balance=wallet_balance,
    )
    return jsonify(success=True, message="Coupon applied successfully.", coupon=coupon.to_dict(), totals=totals)


@checkout_bp.route("/api/checkout/place-order", methods=["POST"])
def checkout_place_order():
    csrf = _require_csrf()
    if csrf:
        return csrf
    data = request.get_json(silent=True) or {}
    result = place_order(
        contact=data.get("contact") or {},
        address=data.get("address") or {},
        shipping_method=(data.get("shippingMethod") or "standard").strip(),
        payment_method=(data.get("paymentMethod") or "cod").strip(),
        coupon_code=(data.get("couponCode") or "").strip() or None,
        coins_to_redeem=int(data.get("coinsToRedeem") or 0),
        estimated_delivery=data.get("estimatedDelivery"),
        payment_meta=data.get("paymentMeta") or {},
    )
    if result.get("error"):
        return _json_error(result["error"])
    return jsonify(success=True, order=result["order"], redirect=result["redirect"])


@checkout_bp.route("/api/checkout/track", methods=["POST"])
def checkout_track():
    csrf = _require_csrf()
    if csrf:
        return csrf
    data = request.get_json(silent=True) or {}
    track_abandonment(
        step=(data.get("step") or "unknown").strip(),
        email=(data.get("email") or "").strip() or None,
        cart_items=get_cart_payload()["items"],
    )
    return jsonify(success=True)


@checkout_bp.route("/api/checkout/addresses", methods=["GET"])
def list_addresses():
    if not current_user.is_authenticated:
        return jsonify(success=True, addresses=[])
    rows = UserAddress.query.filter_by(user_id=current_user.id).order_by(UserAddress.is_default.desc(), UserAddress.id.desc())
    return jsonify(success=True, addresses=[row.to_dict() for row in rows])


@checkout_bp.route("/api/checkout/addresses", methods=["POST"])
@login_required
def create_address():
    csrf = _require_csrf()
    if csrf:
        return csrf
    data = request.get_json(silent=True) or {}
    err = validate_address_payload(data)
    if err:
        return _json_error(err["error"])
    if data.get("isDefault"):
        UserAddress.query.filter_by(user_id=current_user.id).update({"is_default": False})
    row = UserAddress(
        user_id=current_user.id,
        full_name=data["fullName"].strip(),
        mobile=re_sub_mobile(data["mobile"]),
        email=(data.get("email") or current_user.email or "").strip(),
        house=data["house"].strip(),
        street=data["street"].strip(),
        landmark=(data.get("landmark") or "").strip(),
        city=data["city"].strip(),
        state=data["state"].strip(),
        pincode=re_sub_pincode(data["pincode"]),
        country=(data.get("country") or "India").strip(),
        is_default=bool(data.get("isDefault")),
    )
    if not UserAddress.query.filter_by(user_id=current_user.id).count():
        row.is_default = True
    db.session.add(row)
    db.session.commit()
    return jsonify(success=True, address=row.to_dict())


@checkout_bp.route("/api/checkout/addresses/<int:address_id>", methods=["PUT"])
@login_required
def update_address(address_id: int):
    csrf = _require_csrf()
    if csrf:
        return csrf
    row = UserAddress.query.filter_by(id=address_id, user_id=current_user.id).first_or_404()
    data = request.get_json(silent=True) or {}
    err = validate_address_payload(data)
    if err:
        return _json_error(err["error"])
    if data.get("isDefault"):
        UserAddress.query.filter_by(user_id=current_user.id).update({"is_default": False})
    row.full_name = data["fullName"].strip()
    row.mobile = re_sub_mobile(data["mobile"])
    row.email = (data.get("email") or row.email or "").strip()
    row.house = data["house"].strip()
    row.street = data["street"].strip()
    row.landmark = (data.get("landmark") or "").strip()
    row.city = data["city"].strip()
    row.state = data["state"].strip()
    row.pincode = re_sub_pincode(data["pincode"])
    row.country = (data.get("country") or "India").strip()
    row.is_default = bool(data.get("isDefault", row.is_default))
    db.session.commit()
    return jsonify(success=True, address=row.to_dict())


@checkout_bp.route("/api/checkout/addresses/<int:address_id>", methods=["DELETE"])
@login_required
def delete_address(address_id: int):
    csrf = _require_csrf()
    if csrf:
        return csrf
    row = UserAddress.query.filter_by(id=address_id, user_id=current_user.id).first_or_404()
    was_default = row.is_default
    db.session.delete(row)
    db.session.commit()
    if was_default:
        nxt = UserAddress.query.filter_by(user_id=current_user.id).first()
        if nxt:
            nxt.is_default = True
            db.session.commit()
    return jsonify(success=True)


def re_sub_mobile(value: str) -> str:
    import re
    return re.sub(r"\s+", "", str(value or ""))


def re_sub_pincode(value: str) -> str:
    import re
    return re.sub(r"\s+", "", str(value or ""))
