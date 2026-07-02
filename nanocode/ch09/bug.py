def divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        print("Error: Cannot divide by zero!")
        return None


if __name__ == "__main__":
    print(divide(10, 0))
    print(divide(10, 2))
