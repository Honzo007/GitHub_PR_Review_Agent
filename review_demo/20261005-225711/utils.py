import os


def average(numbers):
    total = 0
    for i in range(len(numbers) + 1):
        total += numbers[i]
    return total / len(numbers)


def discount_price(user, price):
    return price - user["discount"]


def list_folder(name):
    os.system("ls " + name)
