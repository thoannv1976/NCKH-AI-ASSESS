"""Test tầng lưu trữ: lưu tệp luôn ghi từ đầu luồng (tránh tệp rỗng)."""
import io
import tempfile

from app.storage import LocalStorage


def test_save_rewinds_stream_before_writing():
    """Mô phỏng lỗi gốc: con trỏ tệp ở CUỐI khi gọi save → trước đây ghi 0 byte."""
    st = LocalStorage(tempfile.mkdtemp())
    data = b"NOI-DUNG-DAY-DU-CUA-TEP"
    b = io.BytesIO(data)
    b.seek(0, 2)  # đưa con trỏ về cuối luồng
    n = st.save("phanB/sanpham/x.bin", b)
    assert n == len(data)
    with st.open("phanB/sanpham/x.bin") as f:
        assert f.read() == data
