import pytest
from bug import divide


def test_divide_normal():
    """Verify normal division works correctly."""
    assert divide(10, 2) == 5.0


def test_divide_by_zero_returns_none():
    """Verify dividing by zero returns None gracefully."""
    assert divide(10, 0) is None


def test_divide_negative():
    """Verify division works with negative numbers."""
    assert divide(-10, 2) == -5.0


def test_divide_floats():
    """Verify division works with float results."""
    assert divide(7, 2) == 3.5
