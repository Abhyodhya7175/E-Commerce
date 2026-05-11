# Flask E-Commerce Project Documentation

This document outlines the features and development progress of the Flask-based E-Commerce application.

## 1. Project Overview
A fully functional E-Commerce platform built with Flask, SQLAlchemy, and Flask-Login. The application features a clean, responsive UI with premium product displays, shopping cart functionality, and user authentication.

## 2. Core Features Implemented

### User Authentication & Management
- **Role-Based Access Control**: Separate flows for 'Admin', 'Customer', and 'Public' visitors.
- **Secure Authentication**: Password hashing using Werkzeug and session management via Flask-Login.
- **Dashboard System**: Dedicated dashboards for customers to manage their profile and for admins to manage inventory.

### Product & Shop Functionality
- **Product Catalog**: Dynamic product grid with category filtering and persistent storage in SQLite.
- **Premium Product Displays**: High-quality product detail pages with image galleries and interactive specifications.
- **Shopping Cart**: Real-time cart management allowing users to add/remove items and calculate totals.
- **Slug-based Routing**: SEO-friendly URLs for product pages (e.g., `/product/mechanical-keyboard-rgb`).

### Review & Rating System
- **Real-time Feedback**: Users can submit star ratings and detailed reviews for products.
- **Dynamic Aggregation**: Automatically calculates average ratings and review counts from the database.
- **Persisted Reviews**: All user feedback is stored and displayed using a structured `Review` model.

## 3. Technical Architecture

### Backend (Python/Flask)
- **Modular Design**: Structured using Flask Blueprints (`auth`, `admin`, `customer`, `public`).
- **Database (SQLAlchemy ORM)**:
  - `User`: Handles accounts and roles.
  - `Product`: Stores item details, pricing, and status.
  - `ProductImage`: Supports multiple high-resolution images per product.
  - `Review`: Stores user ratings and messages linked to specific products.

### Frontend
- **Templates**: Jinja2 templating with a component-based approach (e.g., `product_card.html`).
- **Styles**: Custom CSS including advanced layouts for product detail pages and authentication forms.
- **Interactivity**: Vanilla JavaScript handles cart operations, quantity adjustments, and AJAX review submissions.

## 4. Setup & Installation
1. Create a virtual environment: `python -m venv env`
2. Install dependencies: `pip install -r requirements.txt`
3. Initialize the database: `python init_db.py`
4. Run the application: `python app.py`

## 5. Recent Fixes
- **Review Submission Error**: Fixed a critical issue where the "Submit Review" feature returned a connection error. Implemented the missing backend API handler and updated the frontend to fetch real data.
- **Dynamic Database Loading**: Ensured product data persists correctly across sessions using SQLAlchemy migrations.
