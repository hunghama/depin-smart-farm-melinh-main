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
# NẠP MODULE MINH CHỨNG ĐỂ CHẠY LƯỚI GÁC CỔNG
from backend.provenance import ProvenanceEngine, ProvenanceRecord

client = TestClient(app)

# =====================================================================
# ⚙️ MẠCH NGẮT KHẨN CẤP CHỐNG ĐỐT TIỀN API
# =====================================================================
MAX_DEBUG_ATTEMPTS = 3

class CircuitBreakerException(Exception):
    pass

def verify_budget_safety(attempt_count: int):
    """Mạch ngắt cứng kiểm soát hành vi tự debug vô hạn của AI"""
    if attempt_count > MAX_DEBUG_ATTEMPTS:
        print("\n🚨 [CIRCUIT BREAKER] Phát hiện nguy cơ Vòng lặp Token vô hạn! Đang ngắt van an toàn...")
        raise CircuitBreakerException("Mạch ngắt kích hoạt: Vượt quá giới hạn tài chính cho phép.")


# =====================================================================
# 🧪 CÁC KỊCH BẢN KIỂM THỬ GÁC CỔNG TẦNG API & STORAGE
# =====================================================================

def test_weather_input_sanity_check():
    """Hóa giải Nghi ngờ 7 & 11: Kiểm thử màng lọc dữ liệu đầu vào khí tượng."""
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
    """Kiểm tra Hào bảo vệ Token: Chặn đứng truy cập không hợp lệ."""
    response_blocked = client.get("/api/v1/zalo/broadcast?crop=ngo_ngot&token=SAI_TOKEN")
    assert response_blocked.status_code == 403
    assert "Xác thực thất bại" in response_blocked.json()["detail"]


@patch('backend.main.ai_client')
@patch('backend.main.requests.get')
@patch('backend.main.requests.post')
@patch('backend.storage.MongoStorage.save_provenance_record', return_value=True)
def test_broadcast_flow_success_with_mock_api(mock_save_prov, mock_tg_post, mock_weather_get, mock_gemini_client):
    """MÔ PHỎNG THỰC CHIẾN TOÀN TRÌNH KHÔNG TỐN TIỀN TOKEN API"""
    mock_weather_get.return_value.status_code = 200
    mock_weather_get.return_value.json.return_value = {
        "forecast": {
            "forecastday": [
                {
                    "date": "2026-06-21",
                    "day": {"maxtemp_c": 35.0, "mintemp_c": 28.0, "condition": {"text": "Sunny"}}
                }
            ]
        }
    }

    mock_response = MagicMock()
    mock_response.text = "Thưa bà con, thời tiết ngô ngọt đang rất đẹp, chú ý bón thúc phân đầy đủ vào ngày nắng nóng 35 độ C."
    mock_gemini_client.models.generate_content.return_value = mock_response

    mock_tg_post.return_value.json.return_value = {"ok": True}

    response = client.get("/api/v1/zalo/broadcast?crop=ngo_ngot&days_old=5&token=MÊ_LINH_THƯƠNG_MẠI_2026")
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert "📢 [DỰ BÁO KHUYẾN NÔNG MVP - NGO NOT]" in response.json()["preview"] or "📢 [DỰ BÁO KHUYẾN NÔNG MVP - NGO NGOT]" in response.json()["preview"]
    assert "🔑 [MÃ MINH CHỨNG SỐ VIETGAP]" in response.json()["preview"]


def test_circuit_breaker_execution():
    """Kiểm thử hành vi bảo vệ tài chính của Mạch ngắt khẩn cấp."""
    with pytest.raises(CircuitBreakerException):
        verify_budget_safety(attempt_count=4)


# =====================================================================
# 🧪 KIỂM THỬ HẠ TẦNG MINH CHỨNG NÔNG SẢN TỰ ĐỘNG
# =====================================================================
def test_provenance_engine_immutability_and_contract():
    """Test tính bất biến và màng bảo vệ chống gian lận dữ liệu chứng chỉ."""
    mock_storage = MagicMock()
    mock_storage.save_provenance_record.return_value = True
    
    engine = ProvenanceEngine(storage_client=mock_storage)
    
    record = engine.build_provenance_footprint(
        crop="ngo_ngot",
        stage="Cây non 5 ngày tuổi",
        weather_text="Nhiệt độ 35 độ C",
        ai_text="Nhắc bà con tưới nước giữ ẩm."
    )
    
    assert isinstance(record, ProvenanceRecord)
    assert record.crop_type == "NGO_NGOT"
    assert record.record_id.startswith("REC-")
    assert len(record.verification_hash) == 64
    mock_storage.save_provenance_record.assert_called_once()
    
    record_clone = engine.build_provenance_footprint(
        crop="ngo_ngot",
        stage="Cây non 5 ngày tuổi",
        weather_text="Nhiệt độ 35 độ C",
        ai_text="Nhắc bà con tưới nước giữ ẩm."
    )
    assert record.verification_hash == record_clone.verification_hash


# =====================================================================
# 🧪 GÁC CỔNG TẦNG JSON API TRA CỨU
# =====================================================================
@patch('backend.storage.MongoStorage.get_provenance_record')
def test_get_provenance_endpoint_success(mock_get_record):
    """Siêu thị quét đúng mã -> JSON trả về 200 thành công."""
    mock_get_record.return_value = {
        "_id": "648f1234567890abcdef1234",
        "record_id": "REC-A1B2C3D4E5F6",
        "timestamp": "2026-06-22T08:00:00Z",
        "crop_type": "NGO_NGOT",
        "crop_stage": "Cây non 5 ngày tuổi",
        "weather_telemetry": "Nhiệt độ 35 độ C",
        "ai_directive": "Nhắc bà con tưới nước giữ ẩm.",
        "verification_hash": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
    }
    response = client.get("/api/v1/provenance/REC-A1B2C3D4E5F6")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


@patch('backend.storage.MongoStorage.get_provenance_record')
def test_get_provenance_endpoint_not_found(mock_get_record):
    """Nhập mã fake bậy bạ -> JSON nổ lỗi 404 chặn đứng gian lận."""
    mock_get_record.return_value = None
    response = client.get("/api/v1/provenance/REC-GIA_MAO_9999")
    assert response.status_code == 404


# =====================================================================
# 🔥 THÀNH PHẨM MODULE SÂU: GÁC CỔNG GIAO DIỆN CHỨNG CHỈ MẶT TIỀN HTML (MÃ QR)
# =====================================================================
@patch('backend.storage.MongoStorage.get_provenance_record')
def test_verify_provenance_page_success(mock_get_record):
    """Kịch bản 1: Khách hàng quét mã thật -> Trả về trang HTML chứng chỉ xanh tươi 200 OK."""
    mock_get_record.return_value = {
        "_id": "648f1234567890abcdef1234",
        "record_id": "REC-MATCH12345",
        "timestamp": "2026-06-23T15:00:00Z",
        "crop_type": "NGO_NGOT",
        "crop_stage": "Cây giai đoạn cuối sắp thu hoạch",
        "weather_telemetry": "Xu hướng nắng nóng 37 độ C",
        "ai_directive": "Khuyến nghị tưới tràn giữ ẩm vào chiều mát.",
        "verification_hash": "hash_an_toan_tuyet_doi_tram_phan_tram"
    }

    response = client.get("/verify/REC-MATCH12345")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Chứng Chỉ Minh Chứng Số VietGAP" in response.text
    assert "NGO NGOT" in response.text  # 🔥 ĐÃ SỬA CHÍNH TẢ KHÍT 100% VỚI RENDER ENGINE SÂU
    assert "hash_an_toan_tuyet_doi_tram_phan_tram" in response.text


@patch('backend.storage.MongoStorage.get_provenance_record')
def test_verify_provenance_page_not_found(mock_get_record):
    """Kịch bản 2: Tem giả hoặc hacker dò mã -> Trả về trang báo động đỏ 404."""
    mock_get_record.return_value = None

    response = client.get("/verify/REC-MA_FOKE_GIA_MAO")
    assert response.status_code == 404
    assert "text/html" in response.headers["content-type"]
    assert "MÃ GIAN LẬN HOẶC KHÔNG TỒN TẠI" in response.text
    assert "REC-MA_FOKE_GIA_MAO" in response.text
