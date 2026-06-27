import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

os.environ["CRON_SECRET_TOKEN"] = "MÊ_LINH_THƯƠNG_MẠI_2026"
os.environ["TELEGRAM_BOT_TOKEN"] = "mock_bot_token"
os.environ["TELEGRAM_CHAT_ID"] = "mock_chat_id"
os.environ["GEMINI_API_KEY"] = "mock_gemini_key"
os.environ["WEATHER_API_KEY"] = "mock_weather_key"
os.environ["BASE_URL"] = "http://127.0.0.1:8000"

from backend.main import app
from backend.provenance import ProvenanceEngine, ProvenanceRecord

client = TestClient(app)

# =====================================================================
# ⚙️ MẠCH NGẮT KHẨN CẤP CHỐNG ĐỐT TIỀN API
# =====================================================================
MAX_DEBUG_ATTEMPTS = 3

class CircuitBreakerException(Exception):
    pass

def verify_budget_safety(attempt_count: int):
    if attempt_count > MAX_DEBUG_ATTEMPTS:
        raise CircuitBreakerException("Mạch ngắt kích hoạt: Vượt quá giới hạn tài chính.")


# =====================================================================
# 🧪 CÁC KỊCH BẢN KIỂM THỬ GÁC CỔNG TẦNG API & STORAGE
# =====================================================================
def test_weather_input_sanity_check():
    valid_payload = {"station_name": "Trạm Test", "temperature": 32.5, "humidity": 75.0, "rain": 0.0, "weather_code": 1000}
    with patch('backend.storage.MongoStorage.save_weather_data', return_value=True):
        response = client.post("/api/v1/weather", json=valid_payload)
        assert response.status_code == 201

    invalid_payload = {"station_name": "Trạm Lỗi", "temperature": 32.5, "humidity": 150.0, "rain": 0.0, "weather_code": 1000}
    assert client.post("/api/v1/weather", json=invalid_payload).status_code == 422


def test_broadcast_endpoint_security_lock():
    assert client.get("/api/v1/zalo/broadcast?crop=ngo_ngot&token=SAI").status_code == 403


@patch('backend.main.ai_client')
@patch('backend.main.requests.get')
@patch('backend.main.requests.post')
@patch('backend.storage.MongoStorage.save_provenance_record', return_value=True)
def test_broadcast_flow_success_with_mock_api(mock_save_prov, mock_tg_post, mock_weather_get, mock_gemini_client):
    mock_weather_get.return_value.status_code = 200
    mock_weather_get.return_value.json.return_value = {"forecast": {"forecastday": [{"date": "2026-06-21", "day": {"maxtemp_c": 35.0, "mintemp_c": 28.0, "condition": {"text": "Sunny"}}}]}}
    mock_response = MagicMock()
    mock_response.text = "Thời tiết ngô ngọt đang rất đẹp."
    mock_gemini_client.models.generate_content.return_value = mock_response
    mock_tg_post.return_value.json.return_value = {"ok": True}

    response = client.get("/api/v1/zalo/broadcast?crop=ngo_ngot&days_old=5&token=MÊ_LINH_THƯƠNG_MẠI_2026")
    assert response.status_code == 200
    assert "[TEM QR CODE IN ẤN]" in response.json()["preview"]


def test_circuit_breaker_execution():
    with pytest.raises(CircuitBreakerException):
        verify_budget_safety(4)


# =====================================================================
# 🧪 KIỂM THỬ HẠ TẦNG MINH CHỨNG TỰ ĐỘNG
# =====================================================================
def test_provenance_engine_immutability_and_contract():
    mock_storage = MagicMock()
    mock_storage.save_provenance_record.return_value = True
    engine = ProvenanceEngine(storage_client=mock_storage)
    record = engine.build_provenance_footprint(crop="ngo_ngot", stage="Cây non", weather_text="35 độ", ai_text="Tưới nước.")
    assert isinstance(record, ProvenanceRecord)
    assert record.qr_code_url.startswith("https://api.qrserver.com/v1/create-qr-code/")


# =====================================================================
# 🧪 GÁC CỔNG TẦNG JSON API TRA CỨU (CHECK CHỐNG TĂNG ÁO SỐ LƯỢT QUÉT)
# =====================================================================
@patch('backend.storage.MongoStorage.get_provenance_record')
def test_get_provenance_endpoint_success(mock_get_record):
    mock_get_record.return_value = {"_id": "1", "record_id": "REC-A1B2", "timestamp": "2026", "crop_type": "NGO_NGOT", "crop_stage": "Cây non", "weather_telemetry": "Nắng", "ai_directive": "Tưới", "verification_hash": "abc", "scan_count": 5}
    response = client.get("/api/v1/provenance/REC-A1B2")
    assert response.status_code == 200
    # 🔥 HỢP ĐỒNG AN TOÀN: Truy vấn JSON bắt buộc phải giữ bộ đếm đứng yên
    mock_get_record.assert_called_once_with("REC-A1B2", increment=False)


# =====================================================================
# 🧪 GÁC CỔNG GIAO DIỆN CHỨNG CHỈ (XÁC THỰC BỘ ĐẾM HOẠT ĐỘNG)
# =====================================================================
@patch('backend.storage.MongoStorage.get_provenance_record')
def test_verify_provenance_page_success(mock_get_record):
    mock_get_record.return_value = {"_id": "1", "record_id": "REC-M123", "timestamp": "2026", "crop_type": "NGO_NGOT", "crop_stage": "Thu hoạch", "weather_telemetry": "Nắng", "ai_directive": "Tưới", "verification_hash": "xyz", "scan_count": 42}
    response = client.get("/verify/REC-M123")
    assert response.status_code == 200
    assert "Chứng Chỉ Minh Chứng Số VietGAP" in response.text
    assert "Đã quét 42 lần" in response.text
    # 🔥 HỢP ĐỒNG THỰC ĐỊA: Quét mã HTML mặt tiền bắt buộc phải kích nổ bộ đếm nguyên tử +1
    mock_get_record.assert_called_once_with("REC-M123", increment=True)


# =====================================================================
# 📊 GÁC CỔNG TRANG TRUNG TÂM SỔ CÁI B2B CÔNG KHAI
# =====================================================================
@patch('backend.storage.MongoStorage.get_all_provenance_records')
def test_view_provenance_ledger_hub_success(mock_get_all):
    mock_get_all.return_value = [
        {"_id": "1", "record_id": "REC-AUDIT9999", "timestamp": "2026", "crop_type": "NGO_NGOT", "crop_stage": "Thu hoạch", "weather_telemetry": "Nắng", "ai_directive": "Mát", "verification_hash": "hash", "scan_count": 100}
    ]
    response = client.get("/ledger")
    assert response.status_code == 200
    assert "Sổ Cái Hành Trình" in response.text
    assert "REC-AUDIT9999" in response.text
    assert "100" in response.text  # Xác thực số lượt quét đã hiển thị trên bảng Audit Trail
