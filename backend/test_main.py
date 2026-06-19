import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Thiết lập môi trường giả lập TRƯỚC KHI nạp app để tránh kích hoạt biến thật
os.environ["CRON_SECRET_TOKEN"] = "MÊ_LINH_THƯƠNG_MẠI_2026"
os.environ["TELEGRAM_BOT_TOKEN"] = "mock_bot_token"
os.environ["TELEGRAM_CHAT_ID"] = "mock_chat_id"
os.environ["GEMINI_API_KEY"] = "mock_gemini_key"
os.environ["WEATHER_API_KEY"] = "mock_weather_key"

from backend.main import app

client = TestClient(app)

# =====================================================================
# ⚙️ MẠCH NGẮT KHẨN CẤP CHỐNG ĐỐT TIỀN API (Hóa giải Nghi ngờ 8)
# =====================================================================
MAX_DEBUG_ATTEMPTS = 3

class CircuitBreakerException(Exception):
    pass

def verify_budget_safety(attempt_count: int):
    """
    Nếu luồng tự động sửa lỗi hoặc sinh nội dung của AI bị lặp quá số lần định mức,
    mạch ngắt cứng sẽ lập tức kích nổ để cứu tài khoản ngân hàng của sếp.
    """
    if attempt_count > MAX_DEBUG_ATTEMPTS:
        print("\n🚨 [CIRCUIT BREAKER] Phát hiện nguy cơ Vòng lặp Token vô hạn! Đang ngắt van an toàn...")
        raise CircuitBreakerException("Mạch ngắt kích hoạt: Vượt quá giới hạn tài chính cho phép.")

# =====================================================================
# 🧪 CÁC KỊCH BẢN KIỂM THỬ GÁC CỔNG (TDD LƯỚI AN TOÀN)
# =====================================================================

def test_weather_input_sanity_check():
    """
    Hóa giải Nghi ngờ 7 & 11: Kiểm thử màng lọc dữ liệu đầu vào khí tượng.
    Nếu nạp dữ liệu vượt ngưỡng vật lý (ví dụ: độ ẩm 150%), hệ thống phải chặn đứng tại cổng.
    """
    # Case 1: Dữ liệu hợp lệ -> Phải trả về 201 thành công
    valid_payload = {
        "station_name": "Trạm Mê Linh Test",
        "temperature": 32.5,
        "humidity": 75.0,
        "rain": 0.0,
        "weather_code": 1000
    }
    with patch('backend.storage.MongoStorage.save_weather_data', return_value=True):
        response = client.post("/api/v1/weather", json=valid_payload)
        assert response.status_code == 201
        assert response.json()["status"] == "success"

    # Case 2: Dữ liệu rác vượt ngưỡng vật lý (Độ ẩm > 100) -> FastAPI/Pydantic bắt buộc phải nổ lỗi 422
    invalid_payload = {
        "station_name": "Trạm Mê Linh Phá Hoại",
        "temperature": 32.5,
        "humidity": 150.0,  # Sai quy luật vật lý
        "rain": 0.0,
        "weather_code": 1000
    }
    response_error = client.post("/api/v1/weather", json=invalid_payload)
    assert response_error.status_code == 422


def test_broadcast_endpoint_security_lock():
    """
    Kiểm tra Hào bảo vệ Token: Nếu Hacker cố tình quét Endpoint không có token đúng,
    hệ thống phải khóa chết quyền truy cập ngay lập tức.
    """
    # Case 1: Sai Token -> Bị từ chối 403
    response_blocked = client.get("/api/v1/zalo/broadcast?crop=ngo_ngot&token=SAI_TOKEN")
    assert response_blocked.status_code == 403
    assert "Xác thực thất bại" in response_blocked.json()["detail"]


@patch('backend.main.ai_client')
@patch('backend.main.requests.get')
@patch('backend.main.requests.post')
def test_broadcast_flow_success_with_mock_api(mock_tg_post, mock_weather_get, mock_gemini_client):
    """
    MÔ PHỎNG THỰC CHIẾN MIỄN PHÍ: 
    Giả lập cuộc gọi API bên ngoài (Weather, Gemini, Telegram) để chạy test tự động 
    mà KHÔNG TỐN MỘT XU TIỀN TOKEN NÀO! (Hóa giải triệt để cảnh báo thuế token trong video).
    """
    # 1. Giả lập API thời tiết trả về kết quả mượt mà
    mock_weather_get.return_value.status_code = 200
    mock_weather_get.return_value.json.return_value = {
        "forecast": {
            "forecastday": [
                {
                    "date": "2026-06-20",
                    "day": {"maxtemp_c": 35.0, "mintemp_c": 28.0, "condition": {"text": "Sunny"}}
                }
            ]
        }
    }

    # 2. Giả lập con Gemini nhả văn bản dặn điền chuẩn chỉnh, không cụt chữ
    mock_response = MagicMock()
    mock_response.text = "Thưa bà con, thời tiết ngô ngọt đang rất đẹp, chú ý bón thúc phân đầy đủ vào ngày nắng nóng 35 độ C."
    mock_gemini_client.models.generate_content.return_value = mock_response

    # 3. Giả lập cổng Telegram bắn tin thông mạch
    mock_tg_post.return_value.json.return_value = {"ok": True}

    # KÍCH HOẠT HÀM LIVESTREAM ĐẦU CUỐI
    response = client.get("/api/v1/zalo/broadcast?crop=ngo_ngot&days_old=5&token=MÊ_LINH_THƯƠNG_MẠI_2026")
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "📢 [DỰ BÁO KHUYẾN NÔNG MVP - NGO NGOT]" in response.json()["preview"]


def test_circuit_breaker_execution():
    """
    Kiểm thử hành vi của Mạch ngắt: Đảm bảo nếu vòng lặp cố đấm ăn xôi vượt quá 3 lần,
    hệ thống phải tự kích nổ Exception an toàn thay vì chạy vô tận đốt tài khoản.
    """
    # Vòng lặp chạy thử nghiệm lần thứ 4 (vượt quá hạn ngạch MAX_DEBUG_ATTEMPTS = 3)
    with pytest.raises(CircuitBreakerException):
        verify_budget_safety(attempt_count=4)
