from app import app
from flask_app.extensions import db
from sqlalchemy import text

with app.app_context():
    print("Dropping all tables...")
    db.session.execute(text('SET FOREIGN_KEY_CHECKS = 0;'))
    tables = db.inspect(db.engine).get_table_names()
    for table in tables:
        print(f"  Dropping {table}...")
        db.session.execute(text(f'DROP TABLE IF EXISTS {table}'))
    db.session.execute(text('SET FOREIGN_KEY_CHECKS = 1;'))
    db.session.commit()
    
    print("Creating all tables...")
    db.create_all()
    print("Database reset complete!")
    print("Tables created:")
    for table in db.inspect(db.engine).get_table_names():
        print(f"  - {table}")
