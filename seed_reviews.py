#!/usr/bin/env python3
"""Seed sample reviews into the database"""

from flask_app import create_app
from flask_app.models import Review, Product
from flask_app.extensions import db
from datetime import datetime, timedelta
import random

app = create_app()

SAMPLE_REVIEWS = [
    {"name": "Rahul Kumar", "message": "Great product! Exceeded my expectations. Highly recommended.", "rating": 5},
    {"name": "Priya Singh", "message": "Good quality and fast delivery. Very satisfied with my purchase.", "rating": 5},
    {"name": "Amit Patel", "message": "Value for money. Works as described.", "rating": 4},
    {"name": "Sneha Verma", "message": "Average quality. Expected better but still decent.", "rating": 3},
    {"name": "Rajesh Kumar", "message": "Excellent! Worth every penny.", "rating": 5},
    {"name": "Maya Sharma", "message": "Good product but packaging could be better.", "rating": 4},
    {"name": "Vikram Singh", "message": "Not as good as expected. But acceptable.", "rating": 3},
    {"name": "Anjali Reddy", "message": "Perfect! Exactly what I needed.", "rating": 5},
    {"name": "Sanjay Joshi", "message": "Really impressed with the quality and service.", "rating": 5},
    {"name": "Divya Menon", "message": "Good product, arrived on time.", "rating": 4},
    {"name": "Ravi Nair", "message": "Decent product. Meets the description.", "rating": 4},
    {"name": "Pooja Desai", "message": "Loved it! Fantastic quality.", "rating": 5},
    {"name": "Arjun Kumar", "message": "Satisfactory. Not great but not bad either.", "rating": 3},
    {"name": "Neha Chopra", "message": "Excellent customer service and product quality.", "rating": 5},
    {"name": "Rohan Kapoor", "message": "Very good value for the price point.", "rating": 4},
]

def seed_reviews():
    with app.app_context():
        # Clear existing reviews
        Review.query.delete()
        db.session.commit()

        products = Product.query.filter_by(active=True).all()

        if not products:
            print("No products found. Please add products first.")
            return

        # Add 8-12 reviews per product with varying dates
        for product in products:
            num_reviews = random.randint(8, 12)
            reviews_to_add = random.sample(SAMPLE_REVIEWS, min(num_reviews, len(SAMPLE_REVIEWS)))

            for i, review_data in enumerate(reviews_to_add):
                # Vary the created_at dates
                days_ago = random.randint(1, 90)
                created_at = datetime.utcnow() - timedelta(days=days_ago)

                review = Review(
                    product_id=product.id,
                    name=review_data["name"],
                    message=review_data["message"],
                    rating=review_data["rating"],
                    created_at=created_at
                )
                db.session.add(review)

            db.session.commit()
            avg_rating = product.average_rating
            review_count = product.review_count
            print(f"[OK] {product.name}: {review_count} reviews, avg rating: {avg_rating}")

        print(f"\nSuccessfully seeded reviews for {len(products)} products!")

if __name__ == "__main__":
    seed_reviews()
