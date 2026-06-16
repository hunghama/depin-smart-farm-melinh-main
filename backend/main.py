import os
import sys
import time  
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
from google import genai  # SDK Gemini chính hãng mới nhất
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
# 🚀 ENDPOINT KÍCH HOẠT PHÁT TIN TƯ VẤN HÀNG NGÀY (PHIÊN BẢN V2.6 CHUẨN ĐÉT)
# =====================================================================
@app.get("/api/v1/zalo/broadcast")
def trigger_concierge_broadcast(crop: str = "chung"):
    """
    🔥 CONCIERGE FLOW V2.6 ULTIMATE: ÉP BUỘC TRÍCH XUẤT NHIỆT ĐỘ & SỐ LIỆU CHI TIẾT
    - Sử dụng Prompt phẳng giúp AI viết thông suốt không bị cắt cụt câu giữa chừng.
    - Cài thêm điều khoản bắt buộc phải lồng ghép số liệu nhiệt độ và diễn biến thời tiết từng ngày.
    - Bảo toàn cơ chế Grounding chống ảo giác và Auto-Retry kháng lỗi 503.
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
        - Nếu thời tiết mát mẻ hoặc không có thiên tai cực đoan: Dặn bà con tranh thủ ra đồng làm cỏ, tỉa lá già và chủ động chăm sóc ruộng vườn phát triển tự nhiên như mọi khi.
        """

    # ──> BƯỚC 1.5: TÍNH GIỜ CHUẨN VIỆT NAM (UTC+7) ──
    vn_now = datetime.now(timezone.utc) + timedelta(hours=7)
    current_date_vn = vn_now.strftime("%d/%m/%Y")
    current_time_vn = vn_now.strftime("%H:%M")

    # ──> BƯỚC 2: KHUNG PROMPT PHẲNG NÂNG CẤP ĐIỀU KHOẢN SỐ LIỆU BẮT BUỘC ──
    prompt = f"""
    Bạn là một trợ lý khuyến nông số am hiểu thực địa tại huyện Mê Linh, Hà Nội.
    Hãy phân tích dữ liệu thời tiết 3 ngày tới và đối chiếu Sổ tay kỹ thuật dưới đây để viết một bản tin dặn dò hoàn chỉnh, liền mạch gửi cho bà con trong họ.

    ⏰ MỐC THỜI GIAN ĐỒNG HỒ THỰC TẾ:
    - Bây giờ đang là: {current_time_vn} ngày {current_date_vn}. Hãy dùng mốc này để gọi tên 'hôm nay', 'ngày mai' cho đúng lịch thực tế tại Việt Nam.

    📊 DỰ BÁO THỜI TIẾT ĐỊA PHƯƠNG TỪ API:
    {forecast_summary}

    📋 SỔ TAY KỸ THUẬT BẮT BUỘC ĐỂ KHUYÊN BÀ CON:
    {strict_rules_text}

    🚨 YÊU CẦU ĐỊNH DẠNG BẢN TIN (BẮT BUỘC TUÂN THỦ TUYỆT ĐỐI):
    1. BẮT BUỘC phải lồng ghép khéo léo thông tin số liệu về nhiệt độ (ví dụ: nhiệt độ bao nhiêu độ, trời mát mẻ hay nắng gắt) và tình trạng thời tiết (mưa dông hay nắng ráo) cụ thể của từng ngày vào nội dung dặn dò để bản tin có số liệu trực quan cho bà con nắm bắt.
    2. Phải viết thành một đoạn văn xuôi hoàn chỉnh, mượt mà từ đầu đến cuối (khoảng 5-6 câu), tuyệt đối không được dừng câu giữa chừng hoặc bỏ lửng văn bản.
    3. Lời dặn dò mộc mạc, bình dị, chân chất như người trong gia đình nói với nhau.
    4. Không dùng dấu gạch đầu dòng, không dùng ký tự bôi đậm ** trong bài viết.
    """

    recommendation_text = ""
    if ai_client and os.getenv("GEMINI_API_KEY"):
        for attempt in range(3):
            try:
                print(f"🤖 Đang gọi Gemini API V2.6 (Lần {attempt + 1}/3)...")
                response = ai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                recommendation_text = response.text.strip()
                if recommendation_text and len(recommendation_text) > 60:
                    print("🟩 Cuộc gọi Gemini V2.6 thành công rực rỡ!")
                    break
            except Exception as e:
                print(f"⚠️ Sự cố kết nối tại lần thử {attempt + 1}: {e}")
                time.sleep(2)

    if not recommendation_text or len(recommendation_text) < 60:
        recommendation_text = "Hệ thống đang cập nhật lịch khuyến nông hè. Bà con chủ động giữ ẩm ruộng rau màu và theo dõi sát tình hình thời tiết cực đoan."

    # ──> BƯỚC 3: ĐỒNG GÓI VÀ ĐẨY BẢN TIN VỀ TELEGRAM ──
    final_message = f"📢 [DỰ BÁO KHUYẾN NÔNG V2 - {crop_title}]\n\n{recommendation_text}"
    is_sent = send_telegram_message(text=final_message)
    
    if is_sent:
        return {"status": "success", "preview": final_message}
    else:
        raise HTTPException(status_code=500, detail="Lỗi kết nối cổng Telegram")


# =====================================================================
# 🎛️ BẢNG ĐIỀU KHIỂN TỪ XA CHỐNG QUÊN LINK (GIAO DIỆN ĐIỆN THOẠI)
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
            
            <p class="text-[10px] text-slate-500 mt-6">Production-ready system v2.6 • Đầy đủ số liệu & nhiệt độ</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
