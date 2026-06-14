import os
import sys
from datetime import datetime, timezone  # 🔥 THÊM MỚI: Để tự động đóng dấu thời gian thực UTC
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
            
            # 🔥 THÊM MỚI: Chỉ định collection chứa dữ liệu khí tượng do con bot cào về
            self.weather_collection = self.db["weather_logs"]
            
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
    # 🔥 THÊM MỚI: HÀM LƯU DỮ LIỆU THỜI TIẾT THỜI GIAN THỰC (VÁ LỖI)
    # =====================================================================
    def save_weather_data(self, packet: dict) -> bool:
        """Lưu trữ bản ghi thời tiết tươi từ API vào collection weather_logs"""
        if not self.client:
            print("⚠️ Cảnh báo [Storage]: Mất kết nối database khi lưu dữ liệu thời tiết.")
            return False
        try:
            # Tự động đóng dấu thời gian UTC nếu gói dữ liệu chưa có để phục vụ việc sort giảm dần
            if "timestamp" not in packet:
                packet["timestamp"] = datetime.now(timezone.utc)
                
            self.weather_collection.insert_one(packet)
            print("🟩 [Storage] Găm dữ liệu thời tiết mới vào MongoDB thành công!")
            return True
        except PyMongoError as e:
            print(f"❌ Sự cố lưu dữ liệu thời tiết vào MongoDB Atlas: {e}")
            return False

    # =====================================================================
    # 🔥 THÊM MỚI: INTERFACE ĐỌC DỮ LIỆU THỜI TIẾT MỚI NHẤT CHO FASTAPI
    # =====================================================================
    def get_latest_weather_data(self) -> dict | None:
        """
        Bốc bản ghi thời tiết mới nhất từ collection weather_logs.
        Tự động ép kiểu ObjectId sang string để tránh lỗi JSON Serialization ở FastAPI.
        """
        if not self.client:
            print("⚠️ Cảnh báo [Storage]: Mất kết nối database khi lấy dữ liệu thời tiết.")
            return None
            
        try:
            # Sắp xếp theo trường 'timestamp' giảm dần (-1) và chỉ lấy đúng 1 bản ghi duy nhất
            latest = list(self.weather_collection.find().sort("timestamp", -1).limit(1))
            
            if latest:
                doc = latest[0]
                doc["_id"] = str(doc["_id"])  # Ép kiểu ObjectId thành string để né lỗi JSON của FastAPI
                return doc
                
            return None
        except PyMongoError as e:
            # Cô lập hoàn toàn lỗi PyMongo tại tầng storage
            print(f"❌ Sự cố truy vấn dữ liệu thời tiết trên MongoDB Atlas: {e}")
            return None
