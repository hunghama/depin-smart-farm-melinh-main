import asyncio
import time
import requests
import math

# Cổng nhận dữ liệu từ Backend chạy local hoặc trên Render
API_URL = "http://127.0.0.1:8000/api/v1/sensor"
# Khi nào chạy trên Render thì ông bỏ dấu # ở dòng dưới ra nhé:
# API_URL = "https://depin-smart-farm-melinh-main.onrender.com/api/v1/sensor"

DEVICE_ID = "ESP32_MELINH_01"

def get_sinusoidal_soil_moisture(t):
    base_moisture = 72.5
    variation = 12.5 * math.sin(t / 50.0) 
    return round(base_moisture + variation, 1)

async def run_hardware_simulator():
    print(f"🔌 [HARDWARE] Đang khởi động chip ESP32...")
    print(f"📡 API Gateway: {API_URL}\n" + "-"*50)
    
    tick = 0
    while True:
        try:
            soil_moisture = get_sinusoidal_soil_moisture(tick)
            soil_temp = round(22.0 + (3.0 * math.cos(tick / 50.0)), 1)
            
            payload = {
                "sensor_id": DEVICE_ID,
                "temperature": soil_temp,
                "soil_moisture": soil_moisture,
                "timestamp": int(time.time()),
                "data_hash": "hardware_signature_placeholder"
            }
            
            print(f"⚡ [ESP32] Đất ẩm: {soil_moisture}% | Nhiệt độ đất: {soil_temp}°C")
            response = requests.post(API_URL, json=payload, timeout=3)
            print(f"   ✅ [WiFi] Kết quả truyền: {response.status_code}")
                
        except Exception as e:
            print(f"   ⚠️ [WiFi Error] Lỗi kết nối: {e}")
            
        print("-"*50)
        tick += 1
        await asyncio.sleep(10) # 10 giây bắn một lần để dễ quan sát

if __name__ == "__main__":
    asyncio.run(run_hardware_simulator())
