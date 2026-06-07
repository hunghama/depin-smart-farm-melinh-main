import time
from backend.storage import MongoStorage

def test_mongo_storage_save_success():
    """
    KỊCH BẢN KIỂM THỬ:
    1. Tạo một gói dữ liệu giả lập chuẩn ruộng vườn Mê Linh.
    2. Gọi hàm giao diện phẳng save_sensor_data().
    3. Assert kết quả trả về phải là True.
    """
    # 1. Chuẩn bị gói tin Mock
    mock_packet = {
        "sensor_id": "ML-ZONE-01-TEST",
        "temperature": 28.5,
        "soil_moisture": 72.3,
        "timestamp": int(time.time()),
        "data_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" # Test Hash
    }
    
    # 2. Khởi tạo Storage Module
    storage = MongoStorage()
    
    # 3. Kích hoạt lệnh ghi dữ liệu
    result = storage.save_sensor_data(mock_packet)
    
    # 4. Kiểm thử bắt buộc (Assert)
    assert result is True, "❌ Lỗi: Hàm không trả về True, lưu trữ thất bại!"
    print("\n✅ KIỂM THỬ THÀNH CÔNG: Module Storage đã ghi đè dữ liệu lên Atlas rực rỡ!")

if __name__ == "__main__":
    test_mongo_storage_save_success()