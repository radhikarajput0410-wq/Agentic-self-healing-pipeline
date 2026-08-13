def add_numbers(a, b):
    def is_integer_string(s):
        """Helper to check if a string represents an integer (e.g., "5", "-3")."""
        if not isinstance(s, str):
            return False
        try:
            return float(s).is_integer()
        except ValueError:
            return False

    # Determine if 'a' can be treated as a number
    try:
        num_a = float(a)
        is_a_numeric = True
        is_a_int_like = isinstance(a, int) or is_integer_string(a)
    except (ValueError, TypeError):
        is_a_numeric = False
        is_a_int_like = False

    # Determine if 'b' can be treated as a number
    try:
        num_b = float(b)
        is_b_numeric = True
        is_b_int_like = isinstance(b, int) or is_integer_string(b)
    except (ValueError, TypeError):
        is_b_numeric = False
        is_b_int_like = False

    # Case 1: Both inputs can be treated as numbers
    if is_a_numeric and is_b_numeric:
        result = num_a + num_b
        # If both original inputs were integer types (int or integer-string)
        # and the sum is a whole number, return an integer.
        if is_a_int_like and is_b_int_like and result == int(result):
            return int(result)
        return result  # Otherwise, return the float sum
    # Case 2: At least one input cannot be treated as a number, so concatenate as strings
    else:
        return str(a) + str(b)