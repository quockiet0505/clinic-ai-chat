from typing import Any, Dict, List

class ResponseValidator:
    """
    Validation Layer: Hứng dữ liệu từ BackendClient, kiểm tra tính hợp lệ.
    Biến dữ liệu rỗng/lỗi thành thông điệp chuẩn để chống Hallucination cho LLM.
    """

    @staticmethod
    def validate_list(data: Any, entity_name: str = "dữ liệu") -> List[Dict]:
        if data is None:
            raise ValueError(f"Hệ thống không thể lấy {entity_name} lúc này.")
        if not isinstance(data, list):
            raise ValueError(f"Dữ liệu {entity_name} trả về không đúng định dạng.")
        if len(data) == 0:
            raise ValueError(f"Không tìm thấy {entity_name} phù hợp với yêu cầu.")
        return data

    @staticmethod
    def validate_dict(data: Any, entity_name: str = "dữ liệu") -> Dict:
        if data is None:
            raise ValueError(f"Hệ thống không thể lấy {entity_name} lúc này.")
        if not isinstance(data, dict):
            raise ValueError(f"Dữ liệu {entity_name} trả về không đúng định dạng.")
        if len(data) == 0:
            raise ValueError(f"Không tìm thấy {entity_name} phù hợp với yêu cầu.")
        return data
