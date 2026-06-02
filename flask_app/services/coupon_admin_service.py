"""Admin coupons & promotions — stats, CRUD, bulk generate, analytics."""

from __future__ import annotations

import random
import string
from datetime import datetime, timedelta

from sqlalchemy import func, or_

from ..extensions import db
from ..models import Coupon, LoyaltyReward, Order, Product, ProductBrand, ProductCategory, _json_dump, _json_load


def _parse_dt(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).strip()
    for fmt in ('%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _combine_date_time(date_str, time_str):
    if not date_str:
        return None
    date_part = str(date_str).strip()[:10]
    time_part = (str(time_str).strip() if time_str else '00:00')[:5]
    return _parse_dt(f'{date_part}T{time_part}')


def get_stats():
    now = datetime.utcnow()
    coupons = Coupon.query.filter(Coupon.parent_id.is_(None)).all()
    active = scheduled = promotions = 0
    for c in coupons:
        st = c.compute_status()
        if st == 'active':
            active += 1
        if st == 'scheduled':
            scheduled += 1
        if c.kind == 'promotion' and st in ('active', 'scheduled'):
            promotions += 1

    order_q = Order.query.filter(Order.coupon_code.isnot(None), Order.coupon_code != '')
    total_orders = Order.query.count() or 1
    coupon_orders = order_q.count()
    revenue = db.session.query(func.coalesce(func.sum(Order.grand_total), 0)).filter(
        Order.coupon_code.isnot(None), Order.coupon_code != ''
    ).scalar()
    discounts = db.session.query(func.coalesce(func.sum(Order.coupon_discount), 0)).scalar()
    redemption_rate = round((coupon_orders / total_orders) * 100, 1) if total_orders else 0

    with_coupon_avg = db.session.query(func.avg(Order.grand_total)).filter(
        Order.coupon_code.isnot(None), Order.coupon_code != ''
    ).scalar() or 0
    without_coupon_avg = db.session.query(func.avg(Order.grand_total)).filter(
        or_(Order.coupon_code.is_(None), Order.coupon_code == '')
    ).scalar() or 0
    aov_impact = round(float(with_coupon_avg) - float(without_coupon_avg), 2)

    return {
        'activeCoupons': active,
        'scheduledPromotions': scheduled if promotions == 0 else promotions,
        'revenueGenerated': float(revenue or 0),
        'totalDiscounts': float(discounts or 0),
        'redemptionRate': redemption_rate,
        'aovImpact': aov_impact,
    }


def list_coupons(*, q='', status='', page=1, per_page=15, sort='created_desc'):
    query = Coupon.query.filter(Coupon.parent_id.is_(None))
    if q:
        like = f'%{q.strip()}%'
        query = query.filter(or_(Coupon.code.ilike(like), Coupon.name.ilike(like), Coupon.description.ilike(like)))

    rows = query.all()
    if status:
        rows = [c for c in rows if c.compute_status() == status]

    sort_key = {
        'name_asc': lambda c: (c.name or c.code).lower(),
        'name_desc': lambda c: (c.name or c.code).lower(),
        'code_asc': lambda c: c.code.lower(),
        'usage_desc': lambda c: -(c.used_count or 0),
        'created_desc': lambda c: -(c.id or 0),
    }.get(sort, lambda c: -(c.id or 0))
    reverse = sort in ('name_desc',)
    rows.sort(key=sort_key, reverse=reverse)

    total = len(rows)
    page = max(1, int(page))
    per_page = max(5, min(50, int(per_page)))
    start = (page - 1) * per_page
    page_rows = rows[start : start + per_page]

    return {
        'items': [c.to_dict(admin=True) for c in page_rows],
        'total': total,
        'page': page,
        'perPage': per_page,
        'pages': max(1, (total + per_page - 1) // per_page),
    }


def get_coupon(coupon_id: int):
    coupon = Coupon.query.filter_by(id=coupon_id, parent_id=None).first()
    if not coupon:
        return None
    return coupon.to_dict(admin=True)


def save_coupon(data: dict) -> dict:
    coupon_id = int(data.get('id') or 0)
    code = str(data.get('code') or '').strip().upper()
    if not code:
        return {'error': 'Coupon code is required.'}

    existing = Coupon.query.filter(Coupon.code == code, Coupon.id != coupon_id).first()
    if existing:
        return {'error': 'Coupon code already exists.'}

    coupon = Coupon.query.get(coupon_id) if coupon_id else Coupon()
    if coupon_id and not coupon:
        return {'error': 'Coupon not found.'}

    coupon.name = str(data.get('name') or '').strip() or code
    coupon.code = code
    coupon.description = str(data.get('description') or '').strip()
    coupon.kind = str(data.get('kind') or 'coupon').strip() or 'coupon'
    coupon.discount_type = str(data.get('discountType') or 'percent').strip()
    coupon.discount_value = float(data.get('discountValue') or 0)
    coupon.min_order_amount = float(data.get('minOrderAmount') or 0)
    max_disc = data.get('maxDiscount')
    coupon.max_discount = float(max_disc) if max_disc not in (None, '', 'null') else None
    coupon.buy_x = int(data['buyX']) if data.get('buyX') not in (None, '') else None
    coupon.buy_y = int(data['buyY']) if data.get('buyY') not in (None, '') else None
    coupon.usage_limit = int(data['usageLimit']) if data.get('usageLimit') not in (None, '') else None
    coupon.per_customer_limit = int(data['perCustomerLimit']) if data.get('perCustomerLimit') not in (None, '') else None
    coupon.first_purchase_only = bool(data.get('firstPurchaseOnly'))
    coupon.new_customer_only = bool(data.get('newCustomerOnly'))
    coupon.is_draft = bool(data.get('isDraft'))
    coupon.active = bool(data.get('active', True)) and not coupon.is_draft

    starts = data.get('startsAt')
    start_time = data.get('startTime')
    end_date = data.get('expiresAt') or data.get('endDate')
    end_time = data.get('endTime')
    coupon.starts_at = _parse_dt(starts) or _combine_date_time(
        data.get('startDate'), start_time
    )
    coupon.expires_at = _parse_dt(end_date) or _combine_date_time(
        data.get('endDate'), end_time
    )

    coupon.rules_json = _json_dump(data.get('rules') or [])
    coupon.product_ids_json = _json_dump(data.get('productIds') or [])
    coupon.category_ids_json = _json_dump(data.get('categoryIds') or [])
    coupon.brand_ids_json = _json_dump(data.get('brandIds') or [])
    coupon.exclude_product_ids_json = _json_dump(data.get('excludeProductIds') or [])
    coupon.exclude_category_ids_json = _json_dump(data.get('excludeCategoryIds') or [])
    coupon.flash_sale_json = _json_dump(data.get('flashSale') or {})

    if not coupon_id:
        db.session.add(coupon)
    db.session.commit()
    return {'success': True, 'coupon': coupon.to_dict(admin=True)}


def duplicate_coupon(coupon_id: int) -> dict:
    src = Coupon.query.get(coupon_id)
    if not src:
        return {'error': 'Coupon not found.'}
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    new_code = f'{src.code[:30]}-{suffix}'
    while Coupon.query.filter_by(code=new_code).first():
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        new_code = f'{src.code[:28]}-{suffix}'

    clone = Coupon(
        name=f'{(src.name or src.code)} Copy',
        code=new_code,
        description=src.description,
        kind=src.kind,
        discount_type=src.discount_type,
        discount_value=src.discount_value,
        min_order_amount=src.min_order_amount,
        max_discount=src.max_discount,
        buy_x=src.buy_x,
        buy_y=src.buy_y,
        usage_limit=src.usage_limit,
        per_customer_limit=src.per_customer_limit,
        first_purchase_only=src.first_purchase_only,
        new_customer_only=src.new_customer_only,
        active=False,
        is_draft=True,
        starts_at=src.starts_at,
        expires_at=src.expires_at,
        rules_json=src.rules_json,
        product_ids_json=src.product_ids_json,
        category_ids_json=src.category_ids_json,
        brand_ids_json=src.brand_ids_json,
        exclude_product_ids_json=src.exclude_product_ids_json,
        exclude_category_ids_json=src.exclude_category_ids_json,
        flash_sale_json=src.flash_sale_json,
        used_count=0,
    )
    db.session.add(clone)
    db.session.commit()
    return {'success': True, 'coupon': clone.to_dict(admin=True)}


def delete_coupon(coupon_id: int) -> dict:
    coupon = Coupon.query.get(coupon_id)
    if not coupon:
        return {'error': 'Coupon not found.'}
    Coupon.query.filter_by(parent_id=coupon.id).delete()
    db.session.delete(coupon)
    db.session.commit()
    return {'success': True}


def bulk_action(action: str, ids: list[int]) -> dict:
    coupons = Coupon.query.filter(Coupon.id.in_(ids)).all()
    if not coupons:
        return {'error': 'No coupons selected.'}
    for c in coupons:
        if action == 'activate':
            c.active = True
            c.is_draft = False
        elif action == 'draft':
            c.is_draft = True
            c.active = False
        elif action == 'delete':
            db.session.delete(c)
    db.session.commit()
    return {'success': True, 'count': len(coupons)}


def bulk_generate(data: dict) -> dict:
    prefix = str(data.get('prefix') or 'UC').strip().upper()
    count = min(500, max(1, int(data.get('count') or 10)))
    discount_type = str(data.get('discountType') or 'percent')
    discount_value = float(data.get('discountValue') or 10)
    expires_at = _parse_dt(data.get('expiresAt') or data.get('expiryDate'))

    created = []
    for _ in range(count):
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        code = f'{prefix}-{suffix}'
        if Coupon.query.filter_by(code=code).first():
            continue
        c = Coupon(
            name=f'{prefix} Bulk',
            code=code,
            description='Bulk generated coupon',
            discount_type=discount_type,
            discount_value=discount_value,
            expires_at=expires_at,
            active=True,
            is_draft=False,
            parent_id=None,
        )
        db.session.add(c)
        created.append(code)
    db.session.commit()
    return {'success': True, 'codes': created, 'count': len(created)}


def get_analytics(date_from=None, date_to=None):
    q = Order.query.filter(Order.coupon_code.isnot(None), Order.coupon_code != '')
    if date_from:
        q = q.filter(Order.created_at >= _parse_dt(date_from))
    if date_to:
        end = _parse_dt(date_to)
        if end:
            q = q.filter(Order.created_at <= end + timedelta(days=1))

    orders = q.all()
    usage_by_code = {}
    revenue_by_code = {}
    for o in orders:
        code = o.coupon_code
        usage_by_code[code] = usage_by_code.get(code, 0) + 1
        revenue_by_code[code] = revenue_by_code.get(code, 0) + float(o.grand_total or 0)

    top = sorted(usage_by_code.items(), key=lambda x: -x[1])[:10]
    total_orders = Order.query.count() or 1
    coupon_orders = len(orders)
    conversion = round((coupon_orders / total_orders) * 100, 1)

    daily = {}
    for o in orders:
        if not o.created_at:
            continue
        key = o.created_at.strftime('%Y-%m-%d')
        daily.setdefault(key, {'usage': 0, 'revenue': 0, 'discount': 0})
        daily[key]['usage'] += 1
        daily[key]['revenue'] += float(o.grand_total or 0)
        daily[key]['discount'] += float(o.coupon_discount or 0)

    labels = sorted(daily.keys())[-14:]
    return {
        'usage': [{'code': c, 'count': n, 'revenue': revenue_by_code.get(c, 0)} for c, n in top],
        'conversionRate': conversion,
        'customerAcquisition': coupon_orders,
        'revenueGenerated': sum(revenue_by_code.values()),
        'chart': {
            'labels': labels,
            'usage': [daily.get(d, {}).get('usage', 0) for d in labels],
            'revenue': [daily.get(d, {}).get('revenue', 0) for d in labels],
            'discount': [daily.get(d, {}).get('discount', 0) for d in labels],
        },
    }


def lookup_assignments():
    products = Product.query.filter_by(active=True).order_by(Product.name.asc()).limit(500).all()
    categories = ProductCategory.query.order_by(ProductCategory.name.asc()).all()
    brands = ProductBrand.query.order_by(ProductBrand.name.asc()).all()
    return {
        'products': [{'id': p.id, 'name': p.name, 'category': p.category} for p in products],
        'categories': [{'id': c.id, 'name': c.name} for c in categories],
        'brands': [{'id': b.id, 'name': b.name} for b in brands],
    }


def list_loyalty_rewards():
    return [r.to_dict() for r in LoyaltyReward.query.order_by(LoyaltyReward.coins_required.asc()).all()]


def save_loyalty_reward(data: dict) -> dict:
    rid = int(data.get('id') or 0)
    title = str(data.get('title') or '').strip()
    if not title:
        return {'error': 'Reward title is required.'}
    reward = LoyaltyReward.query.get(rid) if rid else LoyaltyReward()
    if rid and not reward:
        return {'error': 'Reward not found.'}
    reward.title = title
    reward.coins_required = int(data.get('coinsRequired') or 0)
    reward.reward_type = str(data.get('rewardType') or 'coupon')
    rv = data.get('rewardValue')
    reward.reward_value = float(rv) if rv not in (None, '') else None
    reward.expiry_days = int(data['expiryDays']) if data.get('expiryDays') not in (None, '') else None
    reward.coupon_id = int(data['couponId']) if data.get('couponId') else None
    reward.active = bool(data.get('active', True))
    reward.config_json = _json_dump(data.get('config') or {})
    if not rid:
        db.session.add(reward)
    db.session.commit()
    return {'success': True, 'reward': reward.to_dict()}


def delete_loyalty_reward(reward_id: int) -> dict:
    reward = LoyaltyReward.query.get(reward_id)
    if not reward:
        return {'error': 'Reward not found.'}
    db.session.delete(reward)
    db.session.commit()
    return {'success': True}
