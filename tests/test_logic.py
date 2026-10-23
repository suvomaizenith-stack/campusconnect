"""Logic tests. Pure functions only; no DB or AI calls."""
import pytest

from logic.auth import clean_student, hash_password, verify_password


def test_password_round_trip():
    stored = hash_password("s3cret")
    assert verify_password("s3cret", stored)
    assert not verify_password("wrong", stored)


def test_password_hash_is_salted():
    assert hash_password("same") != hash_password("same")


def test_clean_student_trims_and_uppercases_roll():
    assert clean_student("  Asha Rao ", " cs2401 ") == ("Asha Rao", "CS2401")


@pytest.mark.parametrize("name, roll", [("", "CS2401"), ("Asha", ""), ("Asha", "bad roll!")])
def test_clean_student_rejects_bad_input(name, roll):
    with pytest.raises(ValueError):
        clean_student(name, roll)
