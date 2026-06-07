import time
import random
import hashlib
import json

class SmartFarmSimulator:
    def __init__(self, sensor_id: str = "ML_ZONE_01"):
        self.sensor_id = sensor_id

    def _generate_raw_data(self) -> dict:
        """Logic ngầm sinh số ngẫu nhiên được giấu kín hoàn toàn (Private Method)."""
        return {
            "sensor_id": self.sensor_id,
            "temperature": round(random.uniform(24.0, 35.0), 1),
            "soil_moisture": round(random.uniform(15.0, 65.0), 1),
            "timestamp": int(time.time())
        }

    def _calculate_hash(self, data: dict) -> str:
        """Logic mã hóa bảo mật dữ liệu chuẩn DePIN trước khi truyền tải (Private Method)."""
        data_string = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_string.encode('utf-8')).hexdigest()

    def generate_secure_packet(self) -> dict:
        """Giao diện lệnh duy nhất (Shallow Interface) phơi bày ra bên ngoài."""
        raw_data = self._generate_raw_data()
        raw_data["data_hash"] = self._calculate_hash(raw_data)
        return raw_data