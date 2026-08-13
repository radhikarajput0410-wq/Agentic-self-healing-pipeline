def add_numbers(a, b):
    try:
        # Attempt to convert both inputs to float and add them.
        # This handles numeric inputs (int, float) and string representations of numbers.
        return float(a) + float(b)
    except (ValueError, TypeError):
        # If conversion to float fails for either input (e.g., "hello"),
        # or if the types are fundamentally incompatible for float() conversion,
        # then fall back to string concatenation.
        return str(a) + str(b)