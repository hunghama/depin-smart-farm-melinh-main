import os
import sys
from datetime import datetime, timezone  # Để tự động đóng dấu thời gian thực UTC
from pymongo import MongoClient
from pymongo.errors import PyMongoError

class MongoStorage:
    def __init__(self):
        """Khởi tạo kết nối đám mây. Giấu kín URI kết nối trong Environment Variable."""
        self.mongo_uri = os.getenv("MONGO_ATLAS_URI")
        
        if not self.mongo_uri:
            print("❌ LỖI KIẾN TRÚC: Chưa cấu hình biến môi trường MONGO_ATLAS_URI!")
            self.client = None
            return

        try:
            # Thiết lập Connection Pool chuẩn, giới hạn thời gian chờ kết nối (Timeout) là 5 giây
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            self.db = self.client["SmartFarmMeLinh"]
            
            # 1. Giữ nguyên collection cũ cho phần cứng (Gói VIP sau này)
            self.collection = self.db["sensor_logs"]
            
            # 2. Collection chứa dữ liệu khí tượng do con bot cào về
            self.weather_collection = self.db["weather_logs"]
            
            # 3. Collection chứa chứng chỉ số minh chứng nông sản bất biến
            self.provenance_collection = self.db["provenance_logs"]
            
        except Exception as e:
            print(f"❌ Không thể khởi tạo kết nối MongoDB Client: {e}")
            self.client = None

    def save_sensor_data(self, packet: dict) -> bool:
        """INTERFACE PHẲNG DUY NHẤT CHO SENSOR CŨ"""
        if not self.client:
            print("⚠️ Cảnh báo [Storage]: Mất kết nối database. Kích hoạt cơ chế chống sập (Fallback)...")
            return False
        try:
            self.collection.insert_one(packet)
            return True
        except PyMongoError as e:
            print(f"❌ Sự cố lưu trữ MongoDB Atlas: {e}")
            return False

    # =====================================================================
    # 🌤️ HÀM LƯU DỮ LIỆU THỜI TIẾT THỜI GIAN THỰC
    # =====================================================================
    def save_weather_data(self, packet: dict) -> bool:
        """Lưu trữ bản ghi thời tiết tươi từ API vào collection weather_logs"""
        if not self.client:
            print("⚠️ Cảnh báo [Storage]: Mất kết nối database khi lưu dữ liệu thời tiết.")
            return False
        try:
            if "timestamp" not in packet:
                packet["timestamp"] = datetime.now(timezone.utc)
                
            self.weather_collection.insert_one(packet)
            print("🟩 [Storage] Găm dữ liệu thời tiết mới vào MongoDB thành công!")
            return True
        except PyMongoError as e:
            print(f"❌ Sự cố lưu dữ liệu thời tiết vào MongoDB Atlas: {e}")
            return False

    # =====================================================================
    # 🌤️ INTERFACE ĐỌC DỮ LIỆU THỜI TIẾT MỚI NHẤT CHO FASTAPI
    # =====================================================================
    def get_latest_weather_data(self) -> dict | None:
        """Bốc bản ghi thời tiết mới nhất từ collection weather_logs."""
        if not self.client:
            print("⚠️ Cảnh báo [Storage]: Mất kết nối database khi lấy dữ liệu thời tiết.")
            return None
            
        try:
            latest = list(self.weather_collection.find().sort("timestamp", -1).limit(1))
            if latest:
                doc = latest[0]
                doc["_id"] = str(doc["_id"])  # Ép kiểu ObjectId thành string né lỗi JSON
                return doc
            return None
        except PyMongoError as e:
            print(f"❌ Sự cố truy vấn dữ liệu thời tiết trên MongoDB Atlas: {e}")
            return None

    # =====================================================================
    # 🛡️ HÀM ĐÚC CHẾT CHỨNG CHỈ SỐ VIETGAP VÀO DATABASE
    # =====================================================================
    def save_provenance_record(self, record_dict: dict) -> bool:
        """Lưu trữ dấu chân số nông sản bất biến vào MongoDB Atlas."""
        if not self.client:
            print("⚠️ Cảnh báo [Storage]: Mất kết nối database khi lưu chứng chỉ minh chứng.")
            return False
        try:
            if "created_at" not in record_dict:
                record_dict["created_at"] = datetime.now(timezone.utc)
                
            self.provenance_collection.insert_one(record_dict)
            print(f"🟩 [Storage] Đã đúc chết mã minh chứng {record_dict.get('record_id')} vào MongoDB Atlas thành công!")
            return True
        except PyMongoError as e:
            print(f"❌ Sự cố lưu chứng chỉ số vào MongoDB Atlas: {e}")
            return False

    # =====================================================================
    # 🔥 THÊM MỚI SPRINT 3: HÀM TRUY VẾT BỐC CHỨNG CHỈ SỐ TỪ MÃ RECORD_ID
    # =====================================================================
    def get_provenance_record(self, record_id: str) -> dict | None:
        """
        Lùng sục và bốc chính xác chứng chỉ số dựa vào mã record_id.
        Phục vụ cổng tra cứu công khai bằng mã QR của siêu thị.
        """
        if not self.client:
            print("⚠️ Cảnh báo [Storage]: Mất kết nối database khi tra cứu chứng chỉ.")
            return None
            
        try:
            # Tìm kiếm bản ghi khít 100% mã record_id (Ví dụ: REC-A1B2C3D4E5F6)
            record = self.provenance_collection.find_one({"record_id": record_id})
            
            if record:
                record["_id"] = str(record["_id"])  # Ép kiểu ObjectId của MongoDB sang String
                return record
                
            return None
        except PyMongoError as e:
            print(f"❌ Sự cố truy vấn mã minh chứng {record_id} trên MongoDB Atlas: {e}")
            return None
