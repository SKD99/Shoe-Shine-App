import sqlite3
import random
from faker import Faker

# Setup
conn = sqlite3.connect("products.db")
cursor = conn.cursor()
fake = Faker()

# Create table
cursor.execute("""
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    price REAL,
    category TEXT,
    image TEXT,
    link TEXT
)
""")

# Clear old data
cursor.execute("DELETE FROM products")

# Manually defined top picks
products = [
    ("Nike Falcon", 7999, "Men", "shoe.jpg", "https://amazon.com"),
    ("Nike Pegasus", 6499, "Women", "Nike_Pegasus.jpeg", "https://flipkart.com"),
    ("Nike Redstar", 5999, "Kids", "Nike_Redstar.jpg", "https://amazon.com"),
    ("Nike Revolution", 8999, "Sports", "Nike_Revolution.jpeg", "https://flipkart.com"),
    ("Nike Runner", 4999, "Joggers", "Nike_Runner.jpeg", "https://amazon.com"),
    ("Nike Whitetiger", 9999, "Boots", "Nike_Whitetiger.jpg", "https://flipkart.com")
]

cursor.executemany("INSERT INTO products (name, price, category, image, link) VALUES (?, ?, ?, ?, ?)", products)

# Auto-generate 1000 dummy shoes
categories = ["Men", "Women", "Kids", "Sports", "Boots"]
images = ["shoe.jpg", "Nike_Pegasus.jpeg", "Nike_Runner.jpeg", "Nike_Whitetiger.jpg"]
links = ["https://amazon.com", "https://flipkart.com", "https://myntra.com"]

for _ in range(1000):
    name = fake.word().capitalize() + " " + fake.word().capitalize()
    price = round(random.uniform(2500, 12000), 2)
    category = random.choice(categories)
    image = random.choice(images)
    link = random.choice(links)
    
    cursor.execute("INSERT INTO products (name, price, category, image, link) VALUES (?, ?, ?, ?, ?)",
                   (name, price, category, image, link))

# Finalize
conn.commit()
conn.close()

print("✅ Seeded: 6 top products + 1000 dummy shoes successfully.")
