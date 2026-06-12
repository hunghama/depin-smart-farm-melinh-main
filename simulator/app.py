import asyncio
from datetime import datetime
import requests

# =====================================================================
# 📡 CẤU HÌNH ĐƯỜNG DẪN API TRẠM GỐC
# =====================================================================
API_URL = "http://127.0.0.1:8000/api/v1/weather"
# Khi nào deploy lên Render, ông mở dấu # ở dòng dưới ra nhé:
# API_URL = "https://depin-smart-farm-melinh-main.onrender.com/api/v1/weather"

# Tọa độ địa lý khu vực huyện Mê Linh, Hà Nội
LATITUDE = 21.18
LONGITUDE = 105.71
FETCH_INTERVAL = 600  # Thời tiết vĩ mô quét 10 phút (600 giây) một lần là chuẩn bài

async def fetch_and_send_macro_weather():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": ["temperature_2m", "relative_humidity_2m", "rain", "weather_code"],
        "timezone": "Asia/Bangkok",
    }

    print("🌤️ [SKY BOT] Con bot cào thời tiết vĩ mô Mê Linh đã khởi động!")
    print(f"📡 API Nhắm bắn: {API_URL}\n" + "-"*50)

    while True:
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"⏰ [{current_time}] Đang đồng bộ dữ liệu từ trạm vệ tinh Open-Meteo...")

            response = requests.get(url, params=params)

            if response.status_code == 200:
                api_data = response.json()
                current = api_data["current"]

                # Đóng gói gói tin thời tiết vĩ mô gửi sang Backend
                payload = {
                    "station_name": "Trạm khí tượng vĩ mô Mê Linh",
                    "temperature": float(current["temperature_2m"]),
                    "humidity": float(current["relative_humidity_2m"]),
                    "rain": float(current["rain"]),
                    "weather_code": int(current["weather_code"])
                }

                print(f"   📊 Thời tiết trời: {payload['temperature']}°C | Ẩm: {payload['humidity']}% | Mưa: {payload['rain']}mm")
                print("   📥 Đang đẩy dữ liệu vĩ mô sang Backend...")

                # Bắn HTTP POST sang Backend cửa khẩu
                backend_res = requests.post(API_URL, json=payload, timeout=5)

                if backend_res.status_code in [200, 201]:
                    print(f"   🟩 Backend phản hồi: Đồng bộ thời tiết vĩ mô thành công!")
                else:
                    print(f"   🚨 Backend từ chối ({backend_res.status_code}): {backend_res.text}")
            else:
                print(f"   ❌ Lỗi kết nối Open-Meteo: {response.status_code}")

        except Exception as e:
            print(f"   ⚠️ [Error] Sự cố luồng cào thời tiết: {e}")

        print(f"😴 Chờ {FETCH_INTERVAL} giây cho chu kỳ tiếp theo...\n" + "-"*50)
        await asyncio.sleep(FETCH_INTERVAL)

if __name__ == "__main__":
    asyncio.run(fetch_and_send_macro_weather())
