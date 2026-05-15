from flask import Blueprint, render_template, request, jsonify, abort
from ..models import Blog
from ..extensions import db
import re

blog_bp = Blueprint('blog', __name__, url_prefix='/blog')


def _slugify(value: str) -> str:
    """Convert string to URL-friendly slug"""
    value = (value or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "blog-post"


@blog_bp.route('/')
def blog_list():
    """Display all blog posts with pagination"""
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '', type=str)
    
    query = Blog.query.filter_by(published=True).order_by(Blog.created_at.desc())
    
    if category:
        query = query.filter_by(category=category)
    
    # Paginate: 6 posts per page
    posts = query.paginate(page=page, per_page=6)
    
    # Get all categories for filter
    all_categories = db.session.query(Blog.category).distinct().filter(Blog.published == True).all()
    categories = [cat[0] for cat in all_categories if cat[0]]
    
    return render_template(
        'blog/list.html',
        posts=posts,
        categories=categories,
        selected_category=category
    )


@blog_bp.route('/<slug>')
def blog_post(slug):
    """Display single blog post"""
    post = Blog.query.filter_by(slug=slug, published=True).first()
    
    if not post:
        abort(404)
    
    # Increment view count
    post.views += 1
    db.session.commit()
    
    # Get related posts (same category)
    related_posts = Blog.query.filter(
        Blog.category == post.category,
        Blog.id != post.id,
        Blog.published == True
    ).order_by(Blog.created_at.desc()).limit(3).all()
    
    return render_template(
        'blog/post.html',
        post=post,
        related_posts=related_posts
    )


@blog_bp.route('/api/search')
def search_posts():
    """API endpoint to search blog posts"""
    query = request.args.get('q', '', type=str).strip()
    
    if not query or len(query) < 2:
        return jsonify({'success': False, 'message': 'Query too short'}), 400
    
    posts = Blog.query.filter(
        Blog.published == True,
        (Blog.title.ilike(f'%{query}%') | Blog.content.ilike(f'%{query}%'))
    ).order_by(Blog.created_at.desc()).limit(10).all()
    
    results = [
        {
            'id': p.id,
            'title': p.title,
            'slug': p.slug,
            'excerpt': p.excerpt or (p.content[:150] + '...'),
            'category': p.category,
            'created_at': p.created_at.strftime('%Y-%m-%d')
        }
        for p in posts
    ]
    
    return jsonify({'success': True, 'results': results})


@blog_bp.route('/api/posts/<int:post_id>/view', methods=['POST'])
def track_view(post_id):
    """Track blog post views"""
    post = Blog.query.get(post_id)
    if not post:
        return jsonify({'success': False}), 404
    
    post.views += 1
    db.session.commit()
    
    return jsonify({'success': True, 'views': post.views})
