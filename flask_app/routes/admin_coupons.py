"""Coupon & promotions admin routes (registered on admin blueprint)."""

from flask import jsonify, render_template, request
from flask_login import login_required
from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..services import coupon_admin_service as svc
from .admin import admin_bp, admin_required


@admin_bp.route('/coupons')
@login_required
@admin_required
def coupons_page():
    return render_template('admin/coupons.html')


@admin_bp.route('/api/coupons/stats', methods=['GET'])
@login_required
@admin_required
def api_coupon_stats():
    return jsonify(success=True, stats=svc.get_stats())


@admin_bp.route('/api/coupons/list', methods=['GET'])
@login_required
@admin_required
def api_coupon_list():
    data = svc.list_coupons(
        q=request.args.get('q', ''),
        status=request.args.get('status', ''),
        page=request.args.get('page', 1),
        per_page=request.args.get('perPage', 15),
        sort=request.args.get('sort', 'created_desc'),
    )
    return jsonify(success=True, **data)


@admin_bp.route('/api/coupons/<int:coupon_id>', methods=['GET'])
@login_required
@admin_required
def api_coupon_get(coupon_id):
    coupon = svc.get_coupon(coupon_id)
    if not coupon:
        return jsonify(success=False, error='Coupon not found.'), 404
    return jsonify(success=True, coupon=coupon)


@admin_bp.route('/api/coupons/save', methods=['POST'])
@login_required
@admin_required
def api_coupon_save():
    data = request.get_json() or {}
    try:
        result = svc.save_coupon(data)
        if result.get('error'):
            return jsonify(success=False, error=result['error']), 400
        return jsonify(**result)
    except SQLAlchemyError:
        db.session.rollback()
        return jsonify(success=False, error='Database error saving coupon.'), 500


@admin_bp.route('/api/coupons/<int:coupon_id>/duplicate', methods=['POST'])
@login_required
@admin_required
def api_coupon_duplicate(coupon_id):
    result = svc.duplicate_coupon(coupon_id)
    if result.get('error'):
        return jsonify(success=False, error=result['error']), 404
    return jsonify(**result)


@admin_bp.route('/api/coupons/<int:coupon_id>/delete', methods=['POST'])
@login_required
@admin_required
def api_coupon_delete(coupon_id):
    result = svc.delete_coupon(coupon_id)
    if result.get('error'):
        return jsonify(success=False, error=result['error']), 404
    return jsonify(**result)


@admin_bp.route('/api/coupons/bulk-action', methods=['POST'])
@login_required
@admin_required
def api_coupon_bulk_action():
    data = request.get_json() or {}
    action = data.get('action', '')
    ids = [int(i) for i in (data.get('ids') or [])]
    if not ids:
        return jsonify(success=False, error='Select at least one coupon.'), 400
    result = svc.bulk_action(action, ids)
    if result.get('error'):
        return jsonify(success=False, error=result['error']), 400
    return jsonify(**result)


@admin_bp.route('/api/coupons/bulk-generate', methods=['POST'])
@login_required
@admin_required
def api_coupon_bulk_generate():
    data = request.get_json() or {}
    try:
        return jsonify(**svc.bulk_generate(data))
    except (TypeError, ValueError) as exc:
        return jsonify(success=False, error=str(exc)), 400


@admin_bp.route('/api/coupons/analytics', methods=['GET'])
@login_required
@admin_required
def api_coupon_analytics():
    return jsonify(
        success=True,
        analytics=svc.get_analytics(
            request.args.get('from'),
            request.args.get('to'),
        ),
    )


@admin_bp.route('/api/coupons/lookup', methods=['GET'])
@login_required
@admin_required
def api_coupon_lookup():
    return jsonify(success=True, **svc.lookup_assignments())


@admin_bp.route('/api/coupons/loyalty', methods=['GET'])
@login_required
@admin_required
def api_loyalty_list():
    return jsonify(success=True, rewards=svc.list_loyalty_rewards())


@admin_bp.route('/api/coupons/loyalty/save', methods=['POST'])
@login_required
@admin_required
def api_loyalty_save():
    data = request.get_json() or {}
    result = svc.save_loyalty_reward(data)
    if result.get('error'):
        return jsonify(success=False, error=result['error']), 400
    return jsonify(**result)


@admin_bp.route('/api/coupons/loyalty/<int:reward_id>/delete', methods=['POST'])
@login_required
@admin_required
def api_loyalty_delete(reward_id):
    result = svc.delete_loyalty_reward(reward_id)
    if result.get('error'):
        return jsonify(success=False, error=result['error']), 404
    return jsonify(**result)
