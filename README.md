# E-Commerce Web Application

A role-based e-commerce web application built with **Flask** and **MySQL**. The system supports two user roles:

- **Admin**: manages products, users, and orders
- **Customer**: browses products, manages cart, places orders, and tracks order status

## 1. Project Overview

This application is designed as a standalone web app with:

- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **Backend**: Flask (Python)
- **Database**: MySQL

## 2. Core Features

### Authentication and Authorization
- Customer registration
- Email/password login
- Session-based authentication
- Role-based access control
- Admin-only routes

### Product Management
- Add products
- Update products
- Delete or disable products
- View all products
- Product image support

### Product Browsing
- View product catalog
- Search and filter products
- View product details

### Shopping Cart
- Add items to cart
- Remove items from cart
- Update quantity
- View cart total

### Order Management
- Place orders
- View order history
- Track order status
- Admin can update order status

### User Management
- View all users
- Delete users
- Optional role assignment

## 3. Functional Requirements Summary

### Authentication
- Users can register as customers
- Users log in with email and password
- Admin users are redirected to the admin dashboard
- Customers are redirected to the home page

### Role-Based Access Control
- Admin routes are protected
- Customers cannot access admin pages

### Product Management
- Admin can create, edit, delete, and view products
- Product fields: name, description, price, stock, image

### Cart and Checkout
- Customers can add products to cart
- Customers can update quantities and remove items
- Customers can place an order from the cart

### Orders
- Customers can view order history
- Admin can view all orders and update their status

## 4. Database Schema

### Tables

#### Users
Stores admin and customer accounts.

- `id` - primary key
- `name`
- `email` - unique
- `password_hash`
- `role` - `admin` or `customer`
- `created_at`
- `updated_at`

#### Products
Stores catalog items.

- `id` - primary key
- `name`
- `description`
- `price`
- `stock`
- `image_url`
- `is_active`
- `created_at`
- `updated_at`

#### Cart Items
Stores customer cart contents.

- `id` - primary key
- `user_id` - foreign key to users
- `product_id` - foreign key to products
- `quantity`
- `created_at`
- `updated_at`

#### Orders
Stores order summaries.

- `id` - primary key
- `user_id` - foreign key to users
- `total_price`
- `status` - pending, shipped, delivered, canceled
- `shipping_name`
- `shipping_address`
- `shipping_phone`
- `created_at`
- `updated_at`

#### Order Items
Stores products inside each order.

- `id` - primary key
- `order_id` - foreign key to orders
- `product_id` - foreign key to products
- `quantity`
- `unit_price`
- `line_total`

### Relationship Summary
- One user has many cart items
- One user has many orders
- One order has many order items
- One product can appear in many cart items and order items

## 5. Non-Functional Requirements

### Security
- Password hashing using `werkzeug.security`
- Session-based login
- Protection against SQL injection using parameterized queries or ORM

### Performance
- Fast page loading
- Efficient database queries
- Pagination for large datasets

### Usability
- Clean UI
- Responsive design
- Easy navigation

### Reliability
- Error handling for failed operations
- Stable support for multiple users

## 6. System Design

### Architecture
This project follows the **MVC pattern**:

- **Model**: MySQL tables and database logic
- **View**: HTML templates
- **Controller**: Flask routes and business logic

### Suggested Folder Structure
```text
app.py
templates/
static/
```

For a larger version, the structure can be expanded into:

```text
app.py
config.py
models.py
routes/
templates/
static/
```

## 7. Use Cases

### Customer Buys a Product
1. User logs in
2. Browses products
3. Adds item to cart
4. Places order
5. Receives confirmation

### Admin Adds a Product
1. Admin logs in
2. Opens dashboard
3. Enters product details
4. Saves the product

## 8. Implementation Plan

### Phase 1: Setup
- Configure Flask project
- Connect MySQL database
- Set secret key and session handling

### Phase 2: Authentication
- Build register, login, and logout
- Hash passwords
- Redirect users by role

### Phase 3: Product Management
- Build admin product CRUD
- Add image support
- Show active products only

### Phase 4: Product Browsing
- Build home page
- Show product catalog
- Add product detail page
- Add search/filter features

### Phase 5: Cart
- Add cart table and logic
- Add, update, remove cart items
- Validate stock

### Phase 6: Checkout and Orders
- Create checkout page
- Create order records
- Save order items
- Update stock
- Clear cart after purchase

### Phase 7: Order Tracking
- Customer order history
- Admin order list
- Update order status

### Phase 8: User Management and Hardening
- Admin user list
- Delete users
- Add validation and flash messages
- Improve UI and responsiveness

## 9. Future Enhancements
- Payment gateway integration such as Razorpay or Stripe
- Product reviews and ratings
- Wishlist
- Email notifications
- JWT-based authentication

## 10. Conclusion

This project provides a complete role-based e-commerce platform with separate admin and customer functionality. It is designed to be scalable and can be extended later with payments, analytics, and other advanced features.
