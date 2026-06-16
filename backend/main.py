import os
import sys
import time  
import random  
import requests
from datetime import datetime, timedelta, timezone  
from dotenv import load_dotenv

# 🔥 Đóng đinh đường dẫn tuyệt đối từ gốc lên quyền ưu tiên CAO NHẤT
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# 1. Nạp file .env trước khi các module khác khởi chạy
load_dotenv()

from fastapi import FastAPI, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse  
from pydantic import BaseModel, Field
from google import genai  
from google.genai import types  
from backend.storage import MongoStorage
# 📦 Nạp Sổ tay kỹ thuật chống ảo giác
from backend.knowledge import AGRI_KNOWLEDGE_BASE

app = FastAPI(title="Smart Farm Mê Linh API v1 - Telegram Concierge MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

storage = MongoStorage()

# Khởi tạo Client Gemini
try:
    ai_client = genai.Client()
except Exception as e:
    print(f"⚠️ Cảnh báo: Chưa cấu hình được Gemini Client: {e}")
    ai_client = None


# =====================================================================
# 🌤️ RECEIVE WEATHER DATA FROM MANUAL INPUT (OPTIONAL)
# =====================================================================
class WeatherDataInput(BaseModel):
    station_name: str = Field(..., example="Trạm khí tượng vĩ mô Mê Linh")
    temperature: float = Field(..., ge=-10.0, le=60.0)
    humidity: float = Field(..., ge=0.0, le=100.0)
    rain: float = Field(..., ge=0.0)
    weather_code: int = Field(..., description="Mã trạng thái thời tiết")


@app.post("/api/v1/weather", status_code=status.HTTP_201_CREATED)
def receive_weather_data(data: WeatherDataInput):
    packet = data.model_dump()
    db_saved = storage.save_weather_data(packet)
    if not db_saved:
        raise HTTPException(status_code=500, detail="Lưu dữ liệu thời tiết thất bại")
    return {"message": "Dữ liệu thời tiết Mê Linh đã đồng bộ thành công!", "status": "success"}


# =====================================================================
# 📡 PHÂN HỆ BẮN TIN NHẮN VỀ TELEGRAM ADMIN
# =====================================================================
def send_telegram_message(text: str) -> bool:
    """Gọi API Telegram để nã bản tin tư vấn về máy của Hùng"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("⚠️ [Telegram Error] Thiếu cấu hình TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    
    try:
        response = requests.post(url, json=payload, timeout=5)
        res_json = response.json()
        if res_json.get("ok"):
            print("🟩 [Telegram] Đã bắn bản tin về máy Admin thành công!")
            return True
        else:
            print(f"❌ [Telegram API Thất bại]: {res_json}")
            return False
    except Exception as e:
        print(f"🚨 [Telegram Transport Error]: {e}")
        return False


# =====================================================================
# 🚀 ENDPOINT KÍCH HOẠT PHÁT TIN TƯ VẤN HÀNG NGÀY (PHIÊN BẢN CHUYÊN SÂU V2)
# =====================================================================
@app.get("/api/v1/zalo/broadcast")
def trigger_concierge_broadcast(crop: str = "chung"):
    """
    🔥 CONCIERGE FLOW V2.5 KIẾN TRÚC TOÀN DIỆN - PHÁ VỠ CẠM BẪY CHỮ:
    - Bốc dữ liệu DỰ BÁO dài hạn 3 ngày từ WeatherAPI.
    - Sửa đổi Chỉ thị gốc từ "Cấm đoán" sang "Hướng dẫn tích cực" bằng cách chỉ định rõ các từ nối thời gian.
    - Tăng nhẹ Temperature lên 0.4 để giải phóng tư duy ngôn ngữ cho AI, giúp câu viết mượt mà không bị nghẹn câu.
    - Bắn thẳng bản tin hoàn chỉnh về Telegram.
    """
    forecast_summary = ""
    
    # ──> BƯỚC 0: CÀO XU HƯỚNG DỰ BÁO THỜI TIẾT 3 NGÀY ──
    try:
        api_key = os.getenv("WEATHER_API_KEY")
        if api_key:
            url_forecast = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q=21.18,105.71&days=3&aqi=no"
            print(f"📡 Đang bốc dữ liệu dự báo dài hạn cho Mê Linh (Mục tiêu: {crop})...")
            response = requests.get(url_forecast, timeout=5)
            
            if response.status_code == 200:
                forecast_days = response.json()["forecast"]["forecastday"]
                lines = []
                for day in forecast_days:
                    date_str = day["date"]
                    max_temp = day["day"]["maxtemp_c"]
                    min_temp = day["day"]["mintemp_c"]
                    condition = day["day"]["condition"]["text"]
                    lines.append(f"- Ngày {date_str}: Nhiệt độ từ {min_temp}°C đến {max_temp}°C. Trạng thái: {condition}")
                forecast_summary = "\n".join(lines)
            else:
                print(f"❌ WeatherAPI từ chối, mã lỗi: {response.status_code}")
    except Exception as e:
        print(f"⚠️ Cảnh báo lỗi cào dữ liệu dự báo: {e}")

    if not forecast_summary:
        forecast_summary = "- Xu hướng 3 ngày tới: Nắng nóng cao điểm hè, nhiệt độ duy trì mức cao 29-37°C, oi bức về đêm."

    # ──> BƯỚC 1: TRÍCH XUẤT LUẬT CỨNG ĐỂ LÀM GROUNDING ──
    knowledge = AGRI_KNOWLEDGE_BASE.get(crop)
    if knowledge:
        crop_title = crop.upper().replace("_", " ")
        strict_rules_text = "\n".join([f"- {rule}" for rule in knowledge["rules"]])
    else:
        crop_title = "BÀ CON NÔNG SẢN MÊ LINH"
        strict_rules_text = """
        - Nếu thời tiết dự báo nắng nóng gắt: Nhắc bà con chú ý giữ ẩm cho đất trồng, bón phân cân đối và căng lưới lan che nắng.
        - Nếu thời tiết dự báo có mưa dông, mưa lớn: Nhắc bà con khẩn trương kiểm tra bờ ruộng, khơi thông luống rãnh để thoát nước nhanh, tránh ngập úng bộ rễ.
        - Nếu thời tiết mát mẻ hoặc không kích hoạt thiên tai cực đoan: Dặn bà con tranh thủ làm cỏ, tỉa lá già và chủ động chăm sóc ruộng vườn phát triển tự nhiên như mọi khi.
        """

    # ──> BƯỚC 1.5: TÍNH GIỜ CHUẨN VIỆT NAM (UTC+7) ──
    vn_now = datetime.now(timezone.utc) + timedelta(hours=7)
    current_date_vn = vn_now.strftime("%d/%m/%Y")
    current_time_vn = vn_now.strftime("%H:%M")

    # ──> BƯỚC 2: THIẾT LẬP INPUT NỘI DUNG VÀ HỆ THỐNG CHỈ THỊ GỐC ──
    user_content = f"""
    📊 DỰ BÁO THỜI TIẾT 3 NGÀY TỚI TỪ API:
    {forecast_summary}

    📋 SỔ TAY KỸ THUẬT BẮT BUỘC:
    {strict_rules_text}

    ⏰ MỐC THỜI GIAN ĐỒNG HỒ THỰC TẾ:
    - Bây giờ là {current_time_vn} ngày {current_date_vn}. Hãy dùng mốc này để định vị hôm nay/ngày mai cho đúng lịch thực tế tại Việt Nam.
    """

    # 🔥 ĐÃ NÂNG CẤP CHỈ THỊ GỐC SANG HƯỚNG DẪN TÍCH CỰC, XÓA BỎ LỆNH CẤM DỮ DẰN 🔥
    system_instruction_text = """
    Bạn là một trợ lý khuyến nông số thực địa tại huyện Mê Linh, Hà Nội.
    Nhiệm vụ của bạn là dịch dữ liệu thời tiết và luật kỹ thuật được cấp thành lời dặn dò bình dị, chân chất như người trong họ dặn dò nhau.

    📋 QUY TẮC PHÁT NGÔN BẮT BUỘC (BAO GROUNDING):
    1. Chỉ đưa ra khuyến nghị hành động dựa trên các thông tin quy định tại "SỔ TAY KỸ THUẬT BẮT BUỘC" phù hợp với thời tiết dự báo. Tuyệt đối không tự chế tên thuốc bảo vệ thực vật hay hóa chất lạ nằm ngoài danh sách.
    2. Đối chiếu mốc thời gian đồng hồ thực tế để gọi tên 'hôm nay', 'ngày mai' chuẩn xác, tránh ngáo giờ ban đêm.
    3. CẤU TRÚC VĂN BẢN: Hãy viết thành một đoạn văn xuôi liên tục và mượt mà hoàn chỉnh (khoảng 4-5 câu). Hãy dùng các cụm từ nối thời gian như "Đối với hôm nay...", "Sang đến ngày mai...", "Còn như ngày kia..." để liên kết nội dung các ngày lại với nhau. Phân tách các ý bằng dấu chấm câu (.) và dấu phẩy (,) thông thường. Không viết biểu tượng gạch đầu dòng, không dùng ký tự bôi đậm.
    """

    recommendation_text = ""
    if ai_client and os.getenv("GEMINI_API_KEY"):
        config_setup = types.GenerateContentConfig(
            system_instruction=system_instruction_text,  
            temperature=0.4,  # 🔥 Tăng nhẹ lên 0.4 để tăng độ linh hoạt ngôn từ, giải phóng khóa não
            max_output_tokens=500  
        )
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"🤖 Đang nã cuộc gọi tối ưu lên Gemini API (Lần {attempt + 1}/{max_retries})...")
                response = ai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=user_content,
                    config=config_setup
                )
                recommendation_text = response.text.strip()
                if recommendation_text:
                    print("🟩 Gọi Gemini API thành công rực rỡ với cấu hình V2.5!")
                    break
            except Exception as e:
                print(f"⚠️ Phát hiện sự cố Gemini API tại lần thử {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    sleep_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"⏳ Tự động kích hoạt Backoff, nín thở chờ {sleep_time:.2f} giây...")
                    time.sleep(sleep_time)

    if not recommendation_text:
        recommendation_text = "Hệ thống đang cập nhật lịch khuyến nông hè. Bà con chủ động giữ ẩm ruộng rau màu và theo dõi sát tình hình thời tiết cực đoan."

    # ──> BƯỚC 3: ĐỒNG GÓI VÀ ĐẨY BẢN TIN CHUYÊN SÂU VỀ TELEGRAM ──
    final_message = f"📢 [DỰ BÁO KHUYẾN NÔNG V2 - {crop_title}]\n\n{recommendation_text}"
    is_sent = send_telegram_message(text=final_message)
    
    if is_sent:
        return {"status": "success", "preview": final_message}
    else:
        raise HTTPException(status_code=500, detail="Lỗi kết nối cổng Telegram")


# =====================================================================
# 🎛️ BẢNG ĐIỀU KHIỂN TỪ XA CHỐNG QUÊN LINK (DÀNH CHO ĐIỆN THOẠI CỦA HÙNG)
# =====================================================================
@app.get("/", response_class=HTMLResponse)
def remote_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Smart Farm Mê Linh - Remote Panel</title>
        <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    </head>
    <body class="bg-slate-900 text-slate-100 font-sans min-h-screen flex flex-col justify-center items-center p-4">
        <div class="bg-slate-800 p-6 rounded-2xl shadow-xl w-full max-w-md border border-slate-700 text-center">
            <h1 class="text-xl font-bold text-emerald-400 mb-2">🚜 SMART FARM MÊ LINH v2</h1>
            <p class="text-xs text-slate-400 mb-6">Bảng điều khiển phát tin khuyến nông số</p>
            
            <div class="space-y-4">
                <a href="/api/v1/zalo/broadcast" target="_blank" class="block w-full py-3 bg-emerald-600 hover:bg-emerald-500 font-medium rounded-xl transition shadow-md no-underline">
                    📢 Phát Bản Tin Chung (6h Sáng)
                </a>
                <hr class="border-slate-700 my-2">
                <a href="/api/v1/zalo/broadcast?crop=rau_muong" target="_blank" class="block w-full py-3 bg-teal-600 hover:bg-teal-500 font-medium rounded-xl transition shadow-md no-underline">
                    🥬 Kích Hoạt Đội Rau Muống Hè
                </a>
                <a href="/api/v1/zalo/broadcast?crop=muop_bi" target="_blank" class="block w-full py-3 bg-cyan-600 hover:bg-cyan-500 font-medium rounded-xl transition shadow-md no-underline">
                    🥒 Kích Hoạt Hội Mướp - Bí Xanh
                </a>
                <a href="/api/v1/zalo/broadcast?crop=ngo_ngot" target="_blank" class="block w-full py-3 bg-amber-600 hover:bg-amber-500 font-medium rounded-xl transition shadow-md no-underline">
                    🌽 Kích Hoạt Vùng Ngô Ngọt
                </a>
            </div>
            
            <p class="text-[10px] text-slate-500 mt-6">Production-ready system v2.5 • Phá vỡ bẫy logic AI</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
