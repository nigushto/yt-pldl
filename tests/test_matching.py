from ytpldl import matching


def test_detect_variants():
    assert "remix" in matching.detect_variants("Song (XYZ Remix)")
    assert "extended" in matching.detect_variants("Song (Extended Mix)")
    assert matching.detect_variants("Just A Song") == set()


def test_core_title_strips_variants_and_brackets():
    assert matching.core_title("Song (XYZ Remix) [Official Video]") == "song"


def test_title_similarity_ignores_variant_noise():
    assert matching.title_similarity("Song", "Song (Official Video)") >= 95


def test_variant_conflict_rejects_unrequested_remix():
    # YouTube original, SoundCloud remix -> conflict.
    assert matching.variant_conflict("Artist - Song", "Artist - Song (ABC Remix)", False) == "remix"


def test_variant_conflict_allows_matching_variant():
    # Both are the same remix -> no conflict.
    assert matching.variant_conflict("Song (ABC Remix)", "Song (ABC Remix)", False) is None


def test_variant_conflict_extended_opt_in():
    assert matching.variant_conflict("Song", "Song (Extended Mix)", False) == "extended"
    assert matching.variant_conflict("Song", "Song (Extended Mix)", True) is None


def test_duration_ok_within_tolerance():
    ok, _ = matching.duration_ok(200, 202, 3, False)
    assert ok
    ok, _ = matching.duration_ok(200, 210, 3, False)
    assert not ok


def test_duration_ok_extended_prefers_longer():
    ok, _ = matching.duration_ok(200, 320, 3, True)
    assert ok
    ok, _ = matching.duration_ok(200, 150, 3, True)
    assert not ok
