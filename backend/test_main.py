import os
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Thiết lập môi trường giả lập chặt chẽ trước khi app nạp cấu hình
os.environ["CRON_SECRET_TOKEN"] = "MÊ_LINH_THƯƠNG_MẠI_2026"
os.environ["TELEGRAM_BOT_TOKEN"] = "mock_bot_token"
os.environ["TELEGRAM_CHAT_ID"] = "mock_chat_id"
os.environ["GEMINI_API_KEY"] = "mock_gemini_key"
os.environ["WEATHER_API_KEY"] = "mock_weather_key"
os.environ["BASE_URL"] = "http://127.0.0.1:8000"
os.environ["MONGO_ATLAS_URI"] = "mongodb://127.0.0.1:27017/mock_db" # Gài URI test để lọt bộ lọc Lifespan

from backend.main import app
from backend.provenance import ProvenanceEngine, ProvenanceRecord

# Kích hoạt TestClient có bao bọc quản lý vòng đời Lifespan Events
client = TestClient(app)

# =====================================================================
# 🧪 CÁC KỊCH BẢN KIỂM THỬ SPRINT 9 (SỔ CÁI, TELEMETRY & LIFESPAN)
# =====================================================================

def test_fastapi_lifespan_startup_contract():
    """
    🔥 TEST MỚI V9: Xác thực bộ gác cổng Lifespan hoạt động hoàn hảo.
    App phải khởi chạy thành công ở chế độ Test Mode mà không bị crash sập nguồn.
    """
    with TestClient(app) as test_ctx_client:
        response = test_ctx_client.get("/")
        assert response.status_code == 200
        assert "TRẠM ĐÚC TEM QR MÊ LINH" in response.text


def test_weather_input_sanity_check():
    valid_payload = {"station_name": "Trạm Test", "temperature": 32.5, "humidity": 75.0, "rain": 0.0, "weather_code": 1000}
    with patch('backend.storage.MongoStorage.save_weather_data', return_value=True):
        response = client.post("/api/v1/weather", json=valid_payload)
        assert response.status_code == 201


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
    mock_response.text = "Lời khuyên từ cố vấn nông nghiệp số Mê Linh xuất sắc hoàn chỉnh dài trên sáu mươi ký tự để vượt qua màng lọc."
    mock_gemini_client.models.generate_content.return_value = mock_response
    mock_tg_post.return_value.json.return_value = {"ok": True}

    response = client.get("/api/v1/zalo/broadcast?crop=ngo_ngot&days_old=5&token=MÊ_LINH_THƯƠNG_MẠI_2026")
    assert response.status_code == 200
    assert "[TEM QR CODE IN ẤN]" in response.json()["preview"]


@patch('backend.storage.MongoStorage.get_provenance_record')
def test_get_provenance_endpoint_success(mock_get_record):
    mock_get_record.return_value = {"_id": "1", "record_id": "REC-A1B2", "timestamp": "2026", "crop_type": "NGO_NGOT", "crop_stage": "Cây non", "weather_telemetry": "Nắng", "ai_directive": "Tới", "verification_hash": "abc", "scan_count": 5}
    response = client.get("/api/v1/provenance/REC-A1B2")
    assert response.status_code == 200
    mock_get_record.assert_called_once_with("REC-A1B2", increment=False)


@patch('backend.storage.MongoStorage.get_provenance_record')
def test_verify_provenance_page_success(mock_get_record):
    mock_get_record.return_value = {"_id": "1", "record_id": "REC-M123", "timestamp": "2026", "crop_type": "NGO_NGOT", "crop_stage": "Thu hoạch", "weather_telemetry": "Nắng", "ai_directive": "Tưới", "verification_hash": "xyz", "scan_count": 42}
    response = client.get("/verify/REC-M123")
    assert response.status_code == 200
    assert "Đã quét 42 lần" in response.text
    mock_get_record.assert_called_once_with("REC-M123", increment=True)


@patch('backend.storage.MongoStorage.get_all_provenance_records')
def test_view_provenance_ledger_hub_success(mock_get_all):
    mock_get_all.return_value = [
        {"_id": "1", "record_id": "REC-AUDIT9999", "timestamp": "2026", "crop_type": "NGO_NGOT", "crop_stage": "Thu hoạch", "weather_telemetry": "Nắng", "ai_directive": "Mát", "verification_hash": "hash", "scan_count": 100}
    ]
    response = client.get("/ledger")
    assert response.status_code == 200
    assert "Sổ Cái Hành Trình" in response.text
    assert "100" in response.text
