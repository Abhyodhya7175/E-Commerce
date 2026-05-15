"""
Script to add sample blog posts to the database
Run with: python add_sample_blogs.py
"""

from flask_app import create_app
from flask_app.models import Blog
from flask_app.extensions import db

app = create_app()

sample_blogs = [
    {
        'title': '10 Must-Have Tech Gadgets for 2024',
        'slug': '10-must-have-tech-gadgets-2024',
        'category': 'Technology',
        'author': 'Sarah Chen',
        'excerpt': 'Discover the latest and greatest tech gadgets that will transform your daily life.',
        'content': '''
<h2>Introduction</h2>
<p>Technology continues to evolve at a rapid pace, and 2024 brings some incredible innovations to the market. Whether you're a tech enthusiast or just looking to upgrade your lifestyle, we've compiled a list of 10 must-have gadgets that deserve a spot in your collection.</p>

<h2>1. Wireless Noise-Cancelling Headphones</h2>
<p>Perfect for work, travel, or everyday use. Premium noise-cancelling technology with 30-hour battery life.</p>

<h2>2. Smart Home Hub</h2>
<p>Control all your smart devices from one central location. Compatible with all major platforms.</p>

<h2>3. Ultra HD 4K Webcam</h2>
<p>Essential for content creators and remote workers. Crystal-clear 4K video quality.</p>

<h2>Conclusion</h2>
<p>These gadgets represent the best of what technology has to offer in 2024. Don't miss out on upgrading your tech setup!</p>
        '''
    },
    {
        'title': 'Fashion Trends This Season',
        'slug': 'fashion-trends-this-season',
        'category': 'Fashion',
        'author': 'Marcus Johnson',
        'excerpt': 'Stay ahead of the curve with our guide to this season\'s hottest fashion trends.',
        'content': '''
<h2>What\'s Hot This Season</h2>
<p>Fashion is constantly evolving, and this season brings exciting new trends to embrace.</p>

<h2>1. Minimalist Aesthetic</h2>
<p>Clean lines, neutral colors, and timeless pieces are dominating the fashion world.</p>

<h2>2. Sustainable Fashion</h2>
<p>Eco-friendly materials and ethical production are becoming mainstream.</p>

<h2>3. Bold Colors</h2>
<p>Don't be afraid to experiment with vibrant hues and eye-catching combinations.</p>

<h2>Final Thoughts</h2>
<p>Fashion is about expressing yourself. Choose pieces that make you feel confident and comfortable!</p>
        '''
    },
    {
        'title': 'Home Decor: Creating Your Perfect Space',
        'slug': 'home-decor-creating-perfect-space',
        'category': 'Home & Living',
        'author': 'Emma Rodriguez',
        'excerpt': 'Transform your home into a sanctuary with these interior design tips and tricks.',
        'content': '''
<h2>Creating Your Ideal Home</h2>
<p>Your home is your sanctuary, and it should reflect your personality and style.</p>

<h2>Color Psychology</h2>
<p>Understand how different colors affect mood and ambiance in each room.</p>

<h2>Furniture Arrangement</h2>
<p>Learn the principles of good furniture placement to maximize space and comfort.</p>

<h2>Lighting Matters</h2>
<p>Proper lighting can completely transform the feel of a room.</p>

<h2>Personal Touches</h2>
<p>Add art, plants, and decorative items that bring joy to your space.</p>
        '''
    },
    {
        'title': 'Fitness Tips for a Healthier You',
        'slug': 'fitness-tips-healthier-you',
        'category': 'Sports & Fitness',
        'author': 'Alex Thompson',
        'excerpt': 'Get fit and stay motivated with our expert fitness advice and workout routines.',
        'content': '''
<h2>Your Fitness Journey</h2>
<p>Starting a fitness routine can be challenging, but with the right guidance, anyone can succeed.</p>

<h2>Set Realistic Goals</h2>
<p>Define clear, achievable fitness goals and track your progress regularly.</p>

<h2>Consistency is Key</h2>
<p>Work out regularly, even if it\'s just 20-30 minutes daily. Consistency beats intensity.</p>

<h2>Nutrition Matters</h2>
<p>A healthy diet complements your fitness routine and accelerates results.</p>

<h2>Stay Motivated</h2>
<p>Find a workout buddy or join a community to stay accountable and motivated.</p>
        '''
    },
    {
        'title': 'The Ultimate Guide to Coffee Culture',
        'slug': 'ultimate-guide-coffee-culture',
        'category': 'Lifestyle',
        'author': 'David Kim',
        'excerpt': 'Explore the world of coffee and learn how to brew the perfect cup.',
        'content': '''
<h2>Welcome to Coffee Culture</h2>
<p>Coffee isn\'t just a beverage; it\'s a lifestyle and a passion for millions around the world.</p>

<h2>Coffee Basics</h2>
<p>Understanding the fundamentals of coffee beans, roasts, and origins.</p>

<h2>Brewing Methods</h2>
<p>From French press to espresso machines, each method offers unique flavor profiles.</p>

<h2>Tasting Notes</h2>
<p>Develop your palate and learn to identify different flavor characteristics.</p>

<h2>Building Your Coffee Ritual</h2>
<p>Make coffee time a mindful, enjoyable part of your daily routine.</p>
        '''
    },
    {
        'title': 'Digital Wellness: Balancing Screen Time',
        'slug': 'digital-wellness-balancing-screen-time',
        'category': 'Technology',
        'author': 'Lisa Patterson',
        'excerpt': 'Learn how to maintain a healthy relationship with technology and digital devices.',
        'content': '''
<h2>The Digital Age</h2>
<p>We\'re more connected than ever, but excessive screen time can impact our health and well-being.</p>

<h2>Understanding Screen Time Effects</h2>
<p>Know the potential impacts of prolonged screen exposure on physical and mental health.</p>

<h2>Setting Boundaries</h2>
<p>Establish healthy limits on device usage and create tech-free zones in your home.</p>

<h2>Digital Detox</h2>
<p>Periodic breaks from screens can significantly improve mental clarity and sleep quality.</p>

<h2>Balance is Everything</h2>
<p>Technology is a tool; use it mindfully and keep it in balance with other activities.</p>
        '''
    }
]

def add_blogs():
    with app.app_context():
        # Check if blogs already exist
        existing_count = Blog.query.count()
        if existing_count > 0:
            print(f"✓ Database already contains {existing_count} blog posts. Skipping insertion.")
            return
        
        # Add sample blogs
        for blog_data in sample_blogs:
            blog = Blog(
                title=blog_data['title'],
                slug=blog_data['slug'],
                category=blog_data['category'],
                author=blog_data['author'],
                excerpt=blog_data['excerpt'],
                content=blog_data['content'],
                featured_image=None,
                published=True,
                views=0
            )
            db.session.add(blog)
        
        db.session.commit()
        print(f"✓ Successfully added {len(sample_blogs)} blog posts to the database!")

if __name__ == '__main__':
    add_blogs()
