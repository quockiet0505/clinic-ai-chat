import pytest

def test_hardcode_moderation_rules():
    # TODO: Khởi tạo module kiểm duyệt và test bộ lọc từ cấm cứng (Blacklist)
    # Ví dụ: "đ.é.o" phải trả về trạng thái REJECTED ngay lập tức mà không cần gọi AI
    pass

def test_fallback_mechanism_for_moderation():
    # TODO: Giả lập (mock) lỗi AI server kiểm duyệt
    # Kiểm tra xem trạng thái bình luận có được đẩy vào hàng đợi PENDING để admin duyệt tay không
    pass
