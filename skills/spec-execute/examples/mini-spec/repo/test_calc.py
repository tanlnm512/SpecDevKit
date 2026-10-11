"""Tests for calc.py — green today; multiply tests arrive with the mini-spec."""
from calc import add, sub

def test_add():
    assert add(2, 3) == 5

def test_sub():
    assert sub(5, 2) == 3
