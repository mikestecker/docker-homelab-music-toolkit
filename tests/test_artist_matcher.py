from app.core.artist_matcher import credit_keys, norm


def test_norm_ignores_case_the_and_punctuation():
    assert norm("The Kry") == norm("kry")
    assert norm("Hillsong & Young") == norm("hillsong and young")
    assert norm("Lofi Hymns.") == norm("lofi hymns")


def test_norm_applies_nfkc():
    # Precomposed "e with acute" vs "e" + a combining acute accent -
    # different code points, same rendered name, equal only after NFKC.
    precomposed = "Café"
    combining = "Café"
    assert precomposed != combining
    assert norm(precomposed) == norm(combining)


def test_credit_keys_splits_on_ampersand():
    keys = credit_keys("Bethel Music & Jenn Johnson")
    assert "bethel music" in keys
    assert "jenn johnson" in keys
    assert norm("Bethel Music & Jenn Johnson") in keys


def test_credit_keys_splits_feat_ft_featuring_with():
    # The separator needs plain spaces around it ("Title feat. Name"), not
    # a parenthetical ("Title (feat. Name)") - matching the credit-list
    # matching rule this was ported from (christian_tag.py's CREDIT_SPLIT),
    # unlike duplicate_finder's separate, bracket-aware feat-credit regex.
    for credit, other in [
        ("Rest feat. Samm Henshaw", "Samm Henshaw"),
        ("Rest ft. Samm Henshaw", "Samm Henshaw"),
        ("Rest featuring Samm Henshaw", "Samm Henshaw"),
        ("Rest with Samm Henshaw", "Samm Henshaw"),
    ]:
        assert norm(other) in credit_keys(credit), credit


def test_credit_keys_of_empty_string_is_empty():
    assert credit_keys("") == set()
