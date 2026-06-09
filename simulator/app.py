import asyncio
from datetime import datetime, timezone
import os  # Thêm dòng này
import motor.motor_asyncio
import requests
from dotenv import load_dotenv  # Thêm dòng này

# Nạp file .env từ thư mục gốc
load_dotenv()

# 1. Bốc chuỗi kết nối từ biến môi trường (Không sợ lộ mật khẩu nữa)
MONGO_DETAILS = os.getenv("MONGO_DETAILS")

# Nếu chạy local mà file .env chưa nhận, dùng tạm bản dự phòng này
if not MONGO_DETAILS:
    MONGO_DETAILS = "mongodb+srv://saicongphihung07072002_db_user:wd1jPuIX0b09GGCU@cluster0.43eiy0n.mongodb.net/?appName=Cluster0"

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DETAILS)
db = client.SmartFarmMeLinh
weather_collection = db.weather_logs
# 2. Tọa độ địa lý khu vực huyện Mê Linh, Hà Nội
LATITUDE = 21.18
LONGITUDE = 105.71

# 3. Tần suất cào dữ liệu (Tính bằng giây) - 15 phút một lần
FETCH_INTERVAL = 900


async def fetch_and_save_weather():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "rain",
            "weather_code",
        ],
        "hourly": "uv_index",
        "timezone": "Asia/Bangkok",
    }

    print("🚀 Con bot cào dữ liệu thời tiết Smart Farm Mê Linh đã kích hoạt thành công!")
    print(f"📡 Tần suất quét: {FETCH_INTERVAL} giây/lần. Đang chạy ngầm...")
    print("-" * 60)

    while True:
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"⏰ [{current_time}] Đang kết nối trạm vệ tinh lấy dữ liệu...")

            response = requests.get(url, params=params)

            if response.status_code == 200:
                api_data = response.json()
                current = api_data["current"]

                # Cấu trúc Schema chuẩn hóa
                weather_doc = {
                    "station_name": "Trạm khí tượng vĩ mô Mê Linh",
                    "coordinates": {"lat": LATITUDE, "lon": LONGITUDE},
                    "timestamp": datetime.now(timezone.utc),
                    "local_time": current["time"],
                    "temperature": current["temperature_2m"],
                    "humidity": current["relative_humidity_2m"],
                    "rain": current["rain"],
                    "weather_code": current["weather_code"],
                    "raw_forecast_data": api_data,
                }

                result = await weather_collection.insert_one(weather_doc)

                print(
                    f"✅ Đã găm dữ liệu vào MongoDB thành công! Document_ID: {result.inserted_id}"
                )
                print(
                    f"📊 Chỉ số thực tế: {weather_doc['temperature']}°C | Độ ẩm: {weather_doc['humidity']}% | Lượng mưa: {weather_doc['rain']}mm"
                )

            else:
                print(
                    f"❌ Lỗi kết nối API Open-Meteo. Mã phản hồi: {response.status_code}"
                )

        except Exception as e:
            print(f"❌ Sự cố luồng cào dữ liệu: {e}")

        print(f"😴 Chờ {FETCH_INTERVAL} giây cho lần cập nhật kế tiếp...\n")
        await asyncio.sleep(FETCH_INTERVAL)


if __name__ == "__main__":
    asyncio.run(fetch_and_save_weather())