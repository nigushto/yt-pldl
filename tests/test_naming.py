from ytpldl import naming


def test_strips_official_video_tag():
    assert naming.clean_title("Artist - Song (Official Video)") == "Artist - Song"


def test_strips_trailing_youtube_id():
    assert naming.clean_title("Artist - Song [dQw4w9WgXcQ]") == "Artist - Song"


def test_keeps_meaningful_parentheticals():
    assert naming.clean_title("Artist - Song (Extended Mix)") == "Artist - Song (Extended Mix)"
    assert naming.clean_title("Artist - Song (XYZ Remix)") == "Artist - Song (XYZ Remix)"


def test_removes_multiple_junk_groups():
    out = naming.clean_title("Song [Official Audio] (HD)")
    assert out == "Song"


def test_sanitize_removes_illegal_chars():
    assert naming.sanitize_filename('a/b:c*d?"e') == "abcde"


def test_sanitize_handles_reserved_names():
    assert naming.sanitize_filename("con").startswith("_")


def test_output_filename_numbering():
    assert naming.output_filename("Song", 3, True) == "03 - Song.wav"
    assert naming.output_filename("Song", 3, False) == "Song.wav"
