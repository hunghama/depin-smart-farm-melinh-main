import hashlib
import json
from sensor_core import SmartFarmSimulator

def test_smart_farm_simulator():
    simulator = SmartFarmSimulator()
    packet = simulator.generate_secure_packet()
    
    print("🔍 Đang kiểm tra cấu trúc gói tin trả về...")
    print(f"Gói tin nhận được: {packet}")
    
    # Assert 1: Kiểm tra đầy đủ các trường cấu trúc JSON theo chuẩn hệ thống
    required_fields = ["sensor_id", "temperature", "soil_moisture", "timestamp", "data_hash"]
    for field in required_fields:
        assert field in packet, f"❌ LỖI: Thiếu trường dữ liệu bắt buộc: '{field}'"
    
    # Assert 2: Kiểm tra tính toàn vẹn bảo mật chống thao túng dữ liệu
    payload_data = {k: v for k, v in packet.items() if k != "data_hash"}
    payload_string = json.dumps(payload_data, sort_keys=True)
    expected_hash = hashlib.sha256(payload_string.encode('utf-8')).hexdigest()
    
    assert packet["data_hash"] == expected_hash, "❌ LỖI: Mã băm không khớp!"
    
    print("\n✅ KIỂM THỬ THÀNH CÔNG: Module đạt chuẩn Deep Module và Bảo mật DePIN!")

if __name__ == "__main__":
    test_smart_farm_simulator()