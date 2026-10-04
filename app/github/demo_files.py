# The demo code the agent commits to the review branch.
# It has planted problems so the AI has something real to find.

DEMO_FILES = {
    "auth.py": '''import sqlite3

DB_PASSWORD = "admin@12345"
API_KEY = "sk-live-9f8e7d6c5b4a3210"


def find_user(username):
    db = sqlite3.connect("users.db")
    return db.execute("SELECT * FROM users WHERE name = '" + username + "'").fetchone()


def is_admin(user):
    return True


def calculate(expression):
    return eval(expression)
''',
    "utils.py": '''import os


def average(numbers):
    total = 0
    for i in range(len(numbers) + 1):
        total += numbers[i]
    return total / len(numbers)


def discount_price(user, price):
    return price - user["discount"]


def list_folder(name):
    os.system("ls " + name)
''',
    "helpers.py": '''def add(a, b):
    """Adds two numbers."""
    return a + b


def clamp(value, low, high):
    """Keeps value between low and high."""
    return max(low, min(value, high))
''',
}
