from off_client import is_barcode

# field name -> (allowed type, description used in error messages)
FIELDS = {
    "name": (str, "a non-empty string"),
    "category": (str, "a non-empty string"),
    "price": ((int, float), "a number of 0 or more"),
    "stock": (int, "a whole number of 0 or more"),
    "barcode": (str, "8 to 14 digits"),
}
OPTIONAL = {"barcode"}  # may be left out on POST


def validate(data, partial=False):
    """Check a request body. Returns (fields, error).

    partial=False (POST): every field except the optional ones is required.
    partial=True (PATCH): only the fields sent are checked, at least one needed.
    """
    if not isinstance(data, dict):
        return None, "Request body must be a JSON object."

    fields = {}
    for key, (kind, description) in FIELDS.items():
        if key not in data:
            if partial or key in OPTIONAL:
                continue
            return None, f"{key} is required."

        value = data[key]
        if isinstance(value, bool) or not isinstance(value, kind):
            return None, f"{key} must be {description}."
        if kind is str:
            value = value.strip()
            if not value or (key == "barcode" and not is_barcode(value)):
                return None, f"{key} must be {description}."
        elif value < 0:
            return None, f"{key} must be {description}."

        fields[key] = float(value) if key == "price" else value

    if partial and not fields:
        return None, "Send at least one of: " + ", ".join(FIELDS) + "."
    return fields, None
