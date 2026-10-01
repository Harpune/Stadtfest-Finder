import pytest

from stadtfest.domain.identity.account import InvalidNameError, name_from_claim, normalize_name


def test_normalize_name_trims() -> None:
    assert normalize_name("  Lena  ") == "Lena"


@pytest.mark.parametrize("value", ["", "   ", "x" * 51])
def test_normalize_name_rejects_invalid_length(value: str) -> None:
    with pytest.raises(InvalidNameError):
        normalize_name(value)


def test_name_from_claim_handles_missing_and_long_values() -> None:
    assert name_from_claim(None) == ""
    assert len(name_from_claim("y" * 80)) == 50
