"""Friend link rules (R12)."""

from stadtfest.domain.collections.friends import LinkOwner, is_token, new_token


def test_tokens_are_random_base64url_with_128_bits() -> None:
    tokens = {new_token() for _ in range(200)}
    assert len(tokens) == 200
    assert all(is_token(token) for token in tokens)
    assert not is_token("abc")
    assert not is_token("A" * 21 + "/")


def test_owner_shows_only_the_initial_of_the_last_name() -> None:
    assert LinkOwner.of("Lena", " beispiel ") == LinkOwner("Lena", "B")
    assert LinkOwner.of("Lena", "") == LinkOwner("Lena", "")
