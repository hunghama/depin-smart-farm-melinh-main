import time
import requests
from sensor_core import SmartFarmSimulator

def main():
    # Khởi tạo đối tượng thông qua Interface chuẩn
    simulator = SmartFarmSimulator()
    backend_url = "http://127.0.0.1:8000/api/v1/sensor" # Cổng Backend tương lai
    session = requests.Session()
    
    print("==================================================")
    print("📡 TRẠM VẬN HÀNH IOT SMART FARM MÊ LINH (DEPIN)")
    print("==================================================")
    
    try:
        while True:
            # 1. Gọi lệnh duy nhất từ giao diện phẳng của Module Sâu
            packet = simulator.generate_secure_packet()
            print(f"📦 Đóng gói mã hóa thành công: {packet['data_hash']}")
            
            # 2. Bắn gói tin sang API của Backend
            try:
                response = session.post(backend_url, json=packet, timeout=3)
                print(f"➡️ Trạng thái gửi Backend: Status Code {response.status_code}")
            except requests.exceptions.ConnectionError:
                print("⚠️ Trạng thái: Backend chưa mở, trạm vẫn tự động đóng gói dữ liệu tại chỗ...")
            
            # 3. Lặp lại chu kỳ nghiêm ngặt 5 giây
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n🛑 Đã tắt trạm vận hành an toàn.")

if __name__ == "__main__":
    main()