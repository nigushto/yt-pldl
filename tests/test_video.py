from ytpldl.video import build_format


def test_prefers_h264_and_caps_height():
    fmt = build_format(1080, prefer_h264=True)
    assert "vcodec^=avc1" in fmt
    assert "height<=1080" in fmt
    # falls back to any streams and then progressive
    assert fmt.endswith("/b")


def test_any_codec_drops_h264_preference():
    fmt = build_format(720, prefer_h264=False)
    assert "avc1" not in fmt
    assert "height<=720" in fmt
