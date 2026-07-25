"""
Endpoint kiểm duyệt bình luận bằng AI.

=== KIẾN TRÚC THỜI GIAN CHẠY ===
AI KHÔNG chạy theo lịch cố định (ví dụ mỗi ngày 1 lần).
Thay vào đó:
  1. Mỗi khi bệnh nhân GỬI đánh giá mới   → Spring Boot @Async gọi endpoint này NGAY LẬP TỨC
  2. Mỗi khi bệnh nhân SỬA nội dung bình luận → Spring Boot @Async gọi lại endpoint này
  3. Mỗi 30 phút Spring Boot @Scheduled QUÉT lại các bình luận PENDING bị kẹt
     (trường hợp AI Server đang tắt/restart lúc bệnh nhân gửi đánh giá)

Kết quả kiểm duyệt được LƯU VĨnh VIỄN vào DB (cột ai_status, ai_moderation_note).
Trang chủ Patient Web chỉ SQL query đơn giản WHERE ai_status='APPROVED' — không gọi AI.
"""

import json
import logging
import re
from enum import Enum

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.llm_service import LLMService

router = APIRouter()
logger = logging.getLogger(__name__)

_llm_service = LLMService()


# =====================================================================
# CÁC QUY TẮC KIỂM DUYỆT CHI TIẾT (4 nhóm, 16 tiêu chí con)
# =====================================================================
class ViolationType(str, Enum):
    TOXIC = "TOXIC"
    SPAM = "SPAM"
    IRRELEVANT = "IRRELEVANT"
    INCOHERENT = "INCOHERENT"
    CLEAN = "CLEAN"


# Danh sách từ thô tục/nhạy cảm thuần túy (100% vi phạm, không phụ thuộc ngữ cảnh)
# Tránh đưa các từ như "lừa đảo", "khởi kiện" vào đây để tránh chặn oan câu phủ định (sẽ do LLM xử lý ở Lớp 2)
TOXIC_KEYWORDS = [
    # Từ tục tĩu viết rõ
    "địt", "đụ", "đéo", "đé0", "đoo", "cặc", "lồn", "buồi", "bùi", "nứng", "đụ má", "đậu má", 
    "chịch", "vcl", "đkm", "đm", "dkm", "dm", "vl", "cl", "sml", "đmm", "đb",
    # Từ xúc phạm/chửi bới nặng nề
    "óc chó", "oc cho", "ngu l", "chó má", "cho ma", "đồ khốn", "đồ chó", "hãm l", "ham l",
    "mất dạy", "mat day", "vô học", "vo hoc", "khốn nạn", "khon nan", "đồ ngu", "thằng điên", 
    "con điên", "thằng chó", "ăn hại", "an hai", "đầu bò", "dau bo", "hãm tài", "ham tai",
    # Tiếng Anh thô tục
    "fuck", "shit", "bitch", "asshole", "idiot", "motherfucker",
    # Từ khóa nhạy cảm / Đe dọa / Khiếu nại (đã bị xóa bỏ khỏi Lớp 1 do dễ bắt nhầm câu phủ định, chuyển sang Lớp 2)
]

# Regex thông minh để bắt các liên kết và số điện thoại
SPAM_PATTERNS = [
    # Bắt link URL đầy đủ hoặc rút gọn (ví dụ: http://, https://, www., shopee.vn, t.me/, zalo.me)
    r"https?://\S+",
    r"www\.\S+",
    r"\b[a-zA-Z0-9.-]+\.(?:com|net|org|vn|edu|gov|xyz|club|me|info|io|tk|ml|ga|cf|gq)\b",
    r"t\.me/\S+",
    r"zalo\.me/\S+",
    r"fb\.me/\S+",
    # Bắt số điện thoại Việt Nam (hỗ trợ cả khoảng trắng, dấu chấm, dấu gạch ngang)
    r"(?:\+84|0)[35789](?:[\s.-]?\d){8}\b",  # Di động
    r"(?:\+84|0)2(?:[\s.-]?\d){9}\b",       # Điện thoại bàn
    # Bắt tài khoản mạng xã hội quảng cáo (ví dụ: @jobhot, @kiemtien)
    r"@[a-zA-Z0-9_]{5,}\b"
]

INCOHERENT_PATTERNS = [
    r"^[^a-zA-Zàáảãạăắặẳẵầấậẩẫâèéẻẽẹêếệểễơớợởỡôốộổỗưứựửữùúủũụìíỉĩịòóỏõọđ\s]{0,10}$",  # Ký tự không phải chữ
    r"^(.)\1{4,}$",           # Lặp 1 ký tự ≥ 5 lần (aaaaaaa)
    r"^[!?.,\s]{0,20}$",      # Chỉ dấu câu
]

# Regex bắt chửi thề viết cách điệu (dùng dấu chấm, gạch ngang, khoảng trắng ở giữa)
TOXIC_REGEX_PATTERNS = [
    r"đ\s*[\._\-]?\s*ị\s*[\._\-]?\s*t",
    r"đ\s*[\._\-]?\s*é\s*[\._\-]?\s*[o0]",
    r"c\s*[\._\-]?\s*ặ\s*[\._\-]?\s*c",
    r"l\s*[\._\-]?\s*ồ\s*[\._\-]?\s*n",
    r"b\s*[\._\-]?\s*u\s*[\._\-]?\s*ồ\s*[\._\-]?\s*i",
    r"\bđ\s*[\._\-]?\s*(?:k\s*[\._\-]?\s*)?m\b",
    r"\bv\s*[\._\-]?\s*(?:c\s*[\._\-]?\s*)?l\b",
    r"v\s*[\._\-]?\s*ã\s*[\._\-]?\s*i\s*[\._\-]?\s*[lđc]"
]


MODERATION_SYSTEM_PROMPT = """Bạn là hệ thống kiểm duyệt bình luận chuyên nghiệp cho ứng dụng y tế phòng khám.

╔══════════════════════════════════════════════════════════════════╗
║              4 NHÓM QUY TẮC KIỂM DUYỆT CHI TIẾT                ║
╚══════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NHÓM 1: [TOXIC] TỪ NGỮ THÔ TỤC / CÔNG KÍCH CÁ NHÂN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.1 TỪ CHỐI nếu có chửi thề, từ ngữ xúc phạm, tiếng lóng tục tĩu.
1.2 TỪ CHỐI nếu tấn công cá nhân bác sĩ/nhân viên bằng tên riêng kèm lời lẽ xúc phạm.
1.3 TỪ CHỐI nếu có lời đe dọa, uy hiếp, tống tiền, kêu gọi tẩy chay phối hợp.
1.4 TỪ CHỐI nếu kỳ thị giới tính, dân tộc, tôn giáo.
1.5 TỪ CHỐI nếu bình luận lan truyền tin đồn y tế thất thiệt, tung tin giả ác ý về phòng khám.
✅ CHO PHÉP phản hồi tiêu cực LỊCH SỰ (ví dụ: "Chờ đợi quá lâu", "Bác sĩ không nhiệt tình").

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NHÓM 2: [SPAM] TIN RÁC / QUẢNG CÁO NGOÀI LỀ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2.1 TỪ CHỐI nếu chứa liên kết website, URL, đường dẫn bất kỳ.
2.2 TỪ CHỐI nếu chứa số điện thoại, địa chỉ email quảng cáo dịch vụ bên ngoài.
2.3 TỪ CHỐI nếu quảng cáo sản phẩm/thuốc/dịch vụ không thuộc phòng khám.
2.4 TỪ CHỐI nếu bình luận trông giống bot: lặp từ ngữ giống hệt nhau nhiều lần.
2.5 TỪ CHỐI nếu bình luận có ý đồ bôi nhọ, chơi xấu từ đối thủ (chê bai và lôi kéo bệnh nhân sang cơ sở khác).
✅ CHO PHÉP đề cập đến tên phòng khám hoặc bác sĩ trong ngữ cảnh đánh giá thật sự.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NHÓM 3: [IRRELEVANT] KHÔNG LIÊN QUAN ĐẾN TRẢI NGHIỆM Y TẾ
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3.1 TỪ CHỐI nếu nội dung hoàn toàn không đề cập gì đến: khám bệnh, điều trị, bác sĩ,
    điều dưỡng, dược sĩ, cơ sở vật chất, thời gian chờ, giá cả khám chữa bệnh.
3.2 TỪ CHỐI nếu chia sẻ tin tức thời sự, chính trị, thể thao không liên quan đến y tế.
3.3 TỪ CHỐI nếu nội dung là truyện kể, thơ, câu đố không liên quan đến trải nghiệm khám.
✅ CHO PHÉP bình luận tổng quát như "Rất hài lòng", "Dịch vụ tốt", "Sẽ quay lại".
✅ CHO PHÉP đề cập cảm xúc/trải nghiệm cá nhân gắn với việc khám bệnh.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NHÓM 4: [INCOHERENT] VÔ NGHĨA / GÕ LINH TINH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4.1 TỪ CHỐI nếu chỉ là chuỗi ký tự ngẫu nhiên không có nghĩa (ví dụ: "asdfghjkl", "qwerty123").
4.2 TỪ CHỐI nếu lặp lại 1 từ/cụm từ vô nghĩa (ví dụ: "oke oke oke", "haha haha haha").
4.3 TỪ CHỐI nếu chỉ có dấu câu, biểu tượng cảm xúc mà không có nội dung thực chất.
4.4 TỪ CHỐI nếu độ dài quá ngắn và không mang thông tin gì (dưới 5 từ không có nghĩa).
✅ CHO PHÉP bình luận ngắn nhưng có nội dung rõ ràng (ví dụ: "Rất tốt!", "Hài lòng.").

╔══════════════════════════════════════════════════════════════════╗
║      HƯỚNG DẪN XỬ LÝ SỐ SAO (RATING) NHẸ NHÀNG & HỢP LÝ          ║
╚══════════════════════════════════════════════════════════════════╝
- Đánh giá 1-2 sao (Sao quá thấp): Để bảo vệ hình ảnh và uy tín phòng khám, mọi đánh giá từ 1-2 sao đều BẮT BUỘC bị từ chối (thiết lập approved = false).
- Đánh giá 3-5 sao: Cho hiển thị nếu không có vi phạm. Tuy nhiên, nếu phát hiện bẫy phá rối (Đánh 5 sao nhưng bình luận chửi thề hoặc chèn quảng cáo) -> vẫn phải chặn (Approved = false).



╔══════════════════════════════════════════════════════════════════╗
║                   QUY TẮC PHÂN TÍCH                             ║
╚══════════════════════════════════════════════════════════════════╝
- Hãy đánh giá bình luận DỰA TRÊN NGỮ CẢNH TỔNG THỂ, không phán xét quá mức một từ riêng lẻ.
- Bình luận TIÊU CỰC LỊCH SỰ (phàn nàn, phê bình xây dựng) → VẪN CHO PHÉP.
- Bình luận CÓ DẤU HIỆU VI PHẠM RÕ RÀNG → TỪ CHỐI.
- Trường hợp KHÔNG CHẮC CHẮN → ƯU TIÊN CHO PHÉP (benefit of the doubt).

╔══════════════════════════════════════════════════════════════════╗
║                   FORMAT TRẢ LỜI BẮT BUỘC                       ║
╚══════════════════════════════════════════════════════════════════╝
Chỉ trả về JSON hợp lệ DUY NHẤT theo format sau, KHÔNG thêm bất kỳ văn bản nào khác:
{
  "approved": true/false,
  "violation_type": "CLEAN" | "TOXIC" | "SPAM" | "IRRELEVANT" | "INCOHERENT",
  "reason": "Lý do cụ thể bằng tiếng Việt (tối đa 100 từ)"
}

Ví dụ output hợp lệ:
{"approved": true, "violation_type": "CLEAN", "reason": "Bình luận lịch sự, liên quan đến trải nghiệm khám bệnh, không vi phạm quy tắc nào."}
{"approved": false, "violation_type": "TOXIC", "reason": "Bình luận chứa từ ngữ xúc phạm nhân viên phòng khám, vi phạm quy tắc 1.2."}
{"approved": false, "violation_type": "SPAM", "reason": "Bình luận chứa liên kết website bên ngoài, vi phạm quy tắc 2.1."}
{"approved": false, "violation_type": "IRRELEVANT", "reason": "Nội dung hoàn toàn không liên quan đến trải nghiệm khám bệnh, vi phạm quy tắc 3.1."}
{"approved": false, "violation_type": "INCOHERENT", "reason": "Bình luận là chuỗi ký tự vô nghĩa, không có nội dung thực chất, vi phạm quy tắc 4.1."}
"""


# =====================================================================
# REQUEST & RESPONSE SCHEMAS
# =====================================================================
class ModerationRequest(BaseModel):
    comment: str
    rating: int = 5


class ModerationResponse(BaseModel):
    approved: bool
    violation_type: str = "CLEAN"
    reason: str


# =====================================================================
# QUICK FILTER: Kiểm tra bằng regex/keyword TRƯỚC khi gọi LLM
# Giúp tiết kiệm tài nguyên Ollama cho các trường hợp vi phạm hiển nhiên
# =====================================================================
def quick_filter(comment: str, rating: int) -> ModerationResponse | None:
    """
    Kiểm tra nhanh bằng pattern matching trước khi gọi LLM.
    Trả về kết quả ngay nếu phát hiện vi phạm rõ ràng.
    Trả về None nếu cần phân tích sâu hơn bằng LLM.
    """
    comment_lower = comment.lower()

    # Kiểm tra số sao thấp (1-2 sao) -> Tự động từ chối luôn để bảo vệ hình ảnh phòng khám
    if rating <= 2:
        return ModerationResponse(
            approved=False,
            violation_type="TOXIC",
            reason=f"Đánh giá sao quá thấp ({rating}/5 sao) không được phép hiển thị công khai."
        )

    # Kiểm tra quá ngắn / vô nghĩa
    if len(comment.strip()) < 3:
        return ModerationResponse(
            approved=True,
            violation_type="CLEAN",
            reason="Bình luận rỗng hoặc quá ngắn, mặc định cho phép."
        )

    # Kiểm tra ký tự vô nghĩa (chỉ dấu câu/số/emoji)
    for pattern in INCOHERENT_PATTERNS:
        if re.fullmatch(pattern, comment.strip(), re.IGNORECASE | re.UNICODE):
            return ModerationResponse(
                approved=False,
                violation_type="INCOHERENT",
                reason="Bình luận vô nghĩa hoặc chỉ là ký tự đặc biệt, vi phạm quy tắc 4.1-4.3."
            )

    # Kiểm tra các mẫu chửi thề cách điệu (Regex) trước
    for pattern in TOXIC_REGEX_PATTERNS:
        if re.search(pattern, comment_lower, re.IGNORECASE):
            return ModerationResponse(
                approved=False,
                violation_type="TOXIC",
                reason="Bình luận chứa từ ngữ chửi thề viết cách điệu, vi phạm quy tắc 1.1."
            )

    # Kiểm tra từ thô tục rõ ràng viết liền
    for keyword in TOXIC_KEYWORDS:
        if keyword in comment_lower:
            return ModerationResponse(
                approved=False,
                violation_type="TOXIC",
                reason=f"Bình luận chứa từ ngữ thô tục/xúc phạm ('{keyword}'), vi phạm quy tắc 1.1."
            )

    # Kiểm tra spam pattern
    for pattern in SPAM_PATTERNS:
        if re.search(pattern, comment_lower, re.IGNORECASE):
            return ModerationResponse(
                approved=False,
                violation_type="SPAM",
                reason=f"Bình luận chứa nội dung spam hoặc quảng cáo (pattern: {pattern}), vi phạm quy tắc 2.x."
            )

    return None  # Cần phân tích sâu hơn bằng LLM


# =====================================================================
# PARSE JSON TỪ RESPONSE CỦA LLM (robust - xử lý nhiều edge cases)
# =====================================================================
def parse_llm_response(raw: str) -> ModerationResponse:
    """
    Parse JSON từ response LLM.
    LLM đôi khi trả về thêm text thừa, markdown fence, hoặc JSON bị incomplete.
    """
    # Thử tìm JSON object trong response
    json_candidates = re.findall(r'\{[^{}]+\}', raw, re.DOTALL)

    for candidate in json_candidates:
        try:
            data = json.loads(candidate)
            approved = bool(data.get("approved", True))
            violation_type = str(data.get("violation_type", "CLEAN" if approved else "UNKNOWN"))
            reason = str(data.get("reason", "Không có lý do cụ thể."))
            return ModerationResponse(approved=approved, violation_type=violation_type, reason=reason)
        except json.JSONDecodeError:
            continue

    # Fallback: cố gắng đọc ý nghĩa từ raw text nếu JSON thất bại
    raw_lower = raw.lower()
    if "false" in raw_lower or "không" in raw_lower or "từ chối" in raw_lower:
        return ModerationResponse(
            approved=False,
            violation_type="UNKNOWN",
            reason=f"LLM gợi ý từ chối nhưng JSON không hợp lệ. Raw: {raw[:100]}"
        )

    # Default: cho phép nếu không parse được
    logger.warning(f"[Moderation] Cannot parse JSON from: {raw[:200]}")
    return ModerationResponse(
        approved=True,
        violation_type="CLEAN",
        reason="Không phân tích được JSON từ AI, mặc định phê duyệt."
    )


# =====================================================================
# ENDPOINT CHÍNH
# =====================================================================
@router.post("/check", response_model=ModerationResponse)
async def check_moderation(request: ModerationRequest):
    """
    Kiểm duyệt bình luận bằng AI 2 lớp:
    Lớp 1 (Quick Filter): Regex + Keyword matching — nhanh, không tốn GPU
    Lớp 2 (LLM): Ollama Qwen 2.5 — phân tích ngữ cảnh sâu hơn

    Được gọi bởi Spring Boot Backend (@Async) ngay sau khi bệnh nhân gửi đánh giá.
    Kết quả được LƯU VĨNH VIỄN vào DB — không bao giờ gọi lại trừ khi bình luận bị sửa.
    """
    comment = (request.comment or "").strip()

    # ── Lớp 1: Quick Filter (không cần GPU) ──
    quick_result = quick_filter(comment, request.rating)
    if quick_result is not None:
        logger.info(
            f"[Moderation/QuickFilter] approved={quick_result.approved} "
            f"type={quick_result.violation_type} | comment='{comment[:60]}'"
        )
        return quick_result

    # ── Lớp 2: LLM Analysis (Ollama Qwen 2.5) ──
    user_prompt = f"""Hãy kiểm duyệt bình luận sau của bệnh nhân theo đúng 4 nhóm quy tắc trong hướng dẫn:

Số sao bệnh nhân chấm: {request.rating}/5
Nội dung bình luận: "{comment}"

Trả về JSON theo đúng format yêu cầu."""

    try:
        raw_response = _llm_service.chat(
            user_message=user_prompt,
            history=None,
            knowledge_context=MODERATION_SYSTEM_PROMPT,
            intent="MODERATION"
        )

        result = parse_llm_response(raw_response)
        logger.info(
            f"[Moderation/LLM] approved={result.approved} type={result.violation_type} "
            f"reason='{result.reason[:80]}' | comment='{comment[:60]}'"
        )
        return result

    except Exception as e:
        logger.error(f"[Moderation/LLM] Error calling Ollama: {e}")
        # Fallback: auto-approve nếu AI Server lỗi (không block trải nghiệm người dùng)
        return ModerationResponse(
            approved=True,
            violation_type="CLEAN",
            reason=f"Lỗi AI Server: {str(e)[:100]}. Mặc định phê duyệt để không block người dùng."
        )
