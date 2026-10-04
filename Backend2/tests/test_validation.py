import pytest

from validation import validate

GOOD = {"name": "Mug", "category": "Kitchen", "price": 5, "stock": 3}


def test_valid_body_is_cleaned():
    fields, error = validate({**GOOD, "name": " Mug "})
    assert error is None
    assert fields == {"name": "Mug", "category": "Kitchen", "price": 5.0, "stock": 3}
    assert isinstance(fields["price"], float)


def test_unknown_fields_are_dropped():
    fields, _ = validate({**GOOD, "user_id": 7, "id": 9, "hack": True})
    assert set(fields) == {"name", "category", "price", "stock"}


def test_barcode_is_optional_but_checked():
    assert validate(GOOD)[1] is None
    assert validate({**GOOD, "barcode": "3274080005003"})[0]["barcode"] == "3274080005003"
    assert validate({**GOOD, "barcode": "12ab"})[1] is not None


def test_partial_checks_only_what_was_sent():
    fields, error = validate({"stock": 4}, partial=True)
    assert (fields, error) == ({"stock": 4}, None)


def test_partial_needs_at_least_one_known_field():
    fields, error = validate({"unknown": 1}, partial=True)
    assert fields is None and "at least one" in error


@pytest.mark.parametrize("body", [None, [], "text", 5])
def test_non_object_bodies_return_a_proper_error_pair(body):
    # regression: this used to return a one-item tuple and crash the caller
    fields, error = validate(body)
    assert fields is None and error == "Request body must be a JSON object."
    fields, error = validate(body, partial=True)
    assert fields is None and error == "Request body must be a JSON object."


@pytest.mark.parametrize("value", [0, 0.0, 12, 12.5])
def test_price_accepts_zero_and_positive_numbers(value):
    assert validate({**GOOD, "price": value})[1] is None


@pytest.mark.parametrize("value", [-0.01, "5", None, True])
def test_price_rejects_everything_else(value):
    assert validate({**GOOD, "price": value})[1] is not None


@pytest.mark.parametrize("value", [1.0, 2.5, "3", None, True, -1])
def test_stock_must_be_a_whole_number_of_zero_or_more(value):
    assert validate({**GOOD, "stock": value})[1] is not None
