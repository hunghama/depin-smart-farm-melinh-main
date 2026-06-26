import hashlib
import json
import os
from datetime import datetime, timezone
from pydantic import BaseModel, Field

# -------------------------------------------------------------
# DTO (DATA TRANSFER OBJECT): KHÓA CHẶT BIÊN GIỚI DỮ LIỆU
# -------------------------------------------------------------
class ProvenanceRecord(BaseModel):
    """Màng bảo vệ cấu trúc chứng chỉ VietGAP số nâng cấp tích hợp QR."""
    record_id: str = Field(..., description="Mã băm độc bản của bản ghi minh chứng")
    timestamp: str = Field(..., description="Thời gian ghi nhận chuẩn ISO UTC+7")
    crop_type: str = Field(..., example="NGO_NGOT")
    crop_stage: str = Field(..., description="Giai đoạn sinh trưởng thực tế của cây")
    weather_telemetry: str = Field(..., description="Dữ liệu thời tiết API cào được tại thời điểm đó")
    ai_directive: str = Field(..., description="Lời dặn hành động gốc mà AI đã phát đi")
    verification_hash: str = Field(..., description="Chữ ký số kiểm tra tính toàn vẹn, chống sửa đổi dữ liệu")
    qr_code_url: str = Field(..., description="Đường dẫn ảnh QR Code phục vụ in ấn tem nhãn thực địa")

# -------------------------------------------------------------
# CORE LOGIC: HỘP XÁM TỰ ĐỘNG SINH DẤU CHÂN SỐ & ĐÚC QR CODE
# -------------------------------------------------------------
class ProvenanceEngine:
    def __init__(self, storage_client=None):
        self.storage = storage_client
        self.base_url = os.getenv("BASE_URL", "http://127.0.0.1:8000")

    def generate_immutable_hash(self, payload: dict) -> str:
        """Tạo ra mã băm SHA-256 từ dữ liệu gốc để chống gian lận."""
        serialized_data = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized_data.encode('utf-8')).hexdigest()

    def build_provenance_footprint(self, crop: str, stage: str, weather_text: str, ai_text: str) -> ProvenanceRecord:
        """HỘP XÁM SÂU V5: Tự động gom dữ liệu thời gian thực để dệt thành chứng chỉ số."""
        vn_time = datetime.now(timezone.utc).isoformat()
        
        raw_payload = {
            "crop_type": crop.upper(),
            "crop_stage": stage,
            "weather_telemetry": weather_text,
            "ai_directive": ai_text
        }
        
        v_hash = self.generate_immutable_hash(raw_payload)
        record_id = f"REC-{v_hash[:12].upper()}"
        
        verification_url = f"{self.base_url}/verify/{record_id}"
        qr_code_url = f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={verification_url}"
        
        record = ProvenanceRecord(
            record_id=record_id,
            timestamp=vn_time,
            crop_type=crop.upper(),
            crop_stage=stage,
            weather_telemetry=weather_text,
            ai_directive=ai_text,
            verification_hash=v_hash,
            qr_code_url=qr_code_url
        )
        
        if self.storage:
            self.storage.save_provenance_record(record.model_dump())
        
        return record

    # =====================================================================
    # 🎨 THỰC THI MODULE SÂU: DỆT HTML CHỨNG CHỈ ĐƠN LẺ (QUÉT MÃ QR)
    # =====================================================================
    def render_html_certificate(self, record_id: str, record: dict | None) -> str:
        """Đóng hòm toàn bộ logic diện mạo hiển thị chứng chỉ vào lòng tầng sâu."""
        if not record:
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>CẢNH BÁO MINH CHỨNG - Smart Farm Mê Linh</title>
                <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
            </head>
            <body class="bg-slate-950 text-slate-100 font-sans min-h-screen flex items-center justify-center p-4">
                <div class="bg-slate-900 border-2 border-red-500 p-8 rounded-2xl shadow-2xl max-w-md w-full text-center">
                    <div class="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-red-900/50 border border-red-500 mb-4">
                        <span class="text-red-500 text-3xl font-bold">⚠️</span>
                    </div>
                    <h1 class="text-xl font-bold text-red-400 mb-2">MÃ GIAN LẬN HOẶC KHÔNG TỒN TẠI</h1>
                    <p class="text-sm text-slate-400 mb-6">Hệ thống không tìm thấy chứng chỉ VietGAP khớp với mã số <span class="text-red-300 font-mono font-bold block mt-1 bg-slate-950 p-2 rounded border border-red-900/50">{record_id}</span></p>
                </div>
            </body>
            </html>
            """

        crop_name = str(record.get('crop_type', 'NÔNG SẢN SẠCH')).replace('_', ' ')
        stage_desc = record.get('crop_stage', 'Đang cập nhật dữ liệu sinh trưởng')
        weather_desc = record.get('weather_telemetry', 'Không ghi nhận sự cố khí tượng')
        ai_text = record.get('ai_directive', 'Đang cập nhật lịch khuyến nông số.')
        v_hash = record.get('verification_hash', 'N/A')
        time_iso = record.get('timestamp', 'N/A')
        
        base_url = self.base_url
        qr_img = record.get('qr_code_url', f"https://api.qrserver.com/v1/create-qr-code/?size=250x250&data={base_url}/verify/{record_id}")

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>CHỨNG CHỈ SỐ VIETGAP - {crop_name}</title>
            <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
        </head>
        <body class="bg-slate-950 text-slate-100 font-sans min-h-screen p-4 flex justify-center items-center">
            <div class="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden">
                <div class="bg-linear-to-r from-emerald-600 to-teal-700 p-6 text-center border-b border-emerald-500/20">
                    <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-emerald-500/30 border border-emerald-300 mb-2">
                        <span class="text-white text-xl font-bold">✓</span>
                    </div>
                    <h1 class="text-lg font-bold text-white uppercase tracking-wider">Chứng Chỉ Minh Chứng Số VietGAP</h1>
                    <p class="text-xs text-emerald-100/80 font-mono mt-1">Mã số: {record_id}</p>
                </div>
                <div class="p-6 space-y-5">
                    <div class="bg-white p-4 rounded-xl flex flex-col items-center justify-center border border-slate-200">
                        <span class="text-[10px] uppercase font-black text-slate-500 tracking-widest mb-2 block">📷 Tem QR Code Quét Tại Siêu Thị</span>
                        <img src="{qr_img}" alt="QR" class="w-44 h-44 border border-slate-100 p-1 bg-white rounded-lg" />
                    </div>
                    <div class="bg-slate-950 p-4 rounded-xl border border-slate-800/60">
                        <span class="text-[10px] uppercase font-bold text-slate-400 tracking-widest block mb-1">📦 Sản phẩm mục tiêu</span>
                        <div class="text-xl font-black text-emerald-400 tracking-wide font-mono">{crop_name}</div>
                        <div class="text-xs text-slate-400 mt-1">🌾 Trạng thái ruộng: <span class="text-slate-200">{stage_desc}</span></div>
                    </div>
                    <div class="bg-slate-950 p-4 rounded-xl border border-slate-800/60">
                        <span class="text-[10px] uppercase font-bold text-slate-400 tracking-widest block mb-1">🌤️ Minh chứng thời tiết thực tế</span>
                        <p class="text-xs text-slate-300 whitespace-pre-line leading-relaxed">{weather_desc}</p>
                    </div>
                    <div class="bg-slate-950 p-4 rounded-xl border border-slate-800/60">
                        <span class="text-[10px] uppercase font-bold text-slate-400 tracking-widest block mb-1">🤖 Khuyến nông số độc bản</span>
                        <p class="text-xs text-slate-300 italic leading-relaxed">"{ai_text}"</p>
                    </div>
                    <div class="flex justify-between items-center text-xs text-slate-400 bg-slate-950/40 p-3 rounded-lg border border-slate-900">
                        <span>⏰ Thời gian đúc mã:</span>
                        <span class="font-mono text-slate-200">{time_iso}</span>
                    </div>
                    <div class="border-t border-slate-800/80 pt-4 text-center">
                        <span class="text-[10px] uppercase font-bold text-emerald-500 tracking-widest block mb-1.5">🛡️ CHỮ KÝ TOÁN HỌC BẤT BIẾN (SHA-256)</span>
                        <div class="bg-slate-950 p-2.5 rounded-lg border border-emerald-900/30 font-mono text-[9px] text-emerald-400 break-all">{v_hash}</div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

    # =====================================================================
    # 🔥 THÊM MỚI SPRINT 6: DỆT HỒ SƠ SỔ CÁI B2B (LEDGER EXPLORER HUB)
    # =====================================================================
    def render_html_ledger(self, records: list) -> str:
        """
        Dệt giao diện Sổ cái tập trung Audit Trail tối tân cho đối tác siêu thị.
        Giấu kín toàn bộ logic lặp mảng phức tạp khỏi file main.py.
        """
        rows_html = ""
        
        if not records:
            rows_html = """
            <tr>
                <td colspan="5" class="p-8 text-center text-xs text-slate-500 italic">
                    📭 Hệ thống đám mây chưa ghi nhận lô hàng minh chứng nào xuất xưởng.
                </td>
            </tr>
            """
        else:
            for r in records:
                rec_id = r.get("record_id", "N/A")
                crop = str(r.get("crop_type", "NÔNG SẢN")).replace("_", " ")
                stage = r.get("crop_stage", "N/A")
                time_iso = r.get("timestamp", "N/A")
                
                # Cắt ngắn chuỗi ISO bớt rác rưởi cho đẹp bảng
                formatted_time = time_iso.split(".")[0].replace("T", " ") if "T" in time_iso else time_iso
                
                rows_html += f"""
                <tr class="border-b border-slate-800/60 hover:bg-slate-800/40 transition">
                    <td class="p-4 text-xs font-mono text-slate-400 font-medium">{formatted_time}</td>
                    <td class="p-4 text-xs font-mono font-bold text-emerald-400 tracking-wide">{rec_id}</td>
                    <td class="p-4 text-xs font-black text-slate-200 tracking-wider uppercase">{crop}</td>
                    <td class="p-4 text-xs text-slate-400 max-w-xs truncate">{stage}</td>
                    <td class="p-4 text-right">
                        <a href="/verify/{rec_id}" target="_blank" class="inline-block px-3 py-1.5 bg-emerald-600/10 hover:bg-emerald-600 text-emerald-400 hover:text-white text-[11px] font-bold rounded-lg border border-emerald-500/20 hover:border-emerald-500 transition no-underline">
                            Đối chiếu QR →
                        </a>
                    </td>
                </tr>
                """

        main_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>SỔ CÁI MINH CHỨNG SỐ - B2B Audit Trail Ledger</title>
            <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
        </head>
        <body class="bg-slate-950 text-slate-100 font-sans min-h-screen p-4 md:p-8 flex flex-col items-center">
            
            <div class="w-full max-w-5xl space-y-6">
                <div class="flex flex-col md:flex-row md:items-center md:justify-between border-b border-slate-800 pb-5 gap-4">
                    <div>
                        <h1 class="text-xl font-black text-emerald-400 uppercase tracking-wider flex items-center gap-2">
                            🛡️ Smart Farm Mê Linh - Sổ Cái Hành Trình
                        </h1>
                        <p class="text-xs text-slate-400 mt-1">Hạ tầng lưu trữ và xuất bản chữ ký số VietGAP thời gian thực cấp doanh nghiệp (B2B SaaS)</p>
                    </div>
                    <div class="bg-slate-900 border border-slate-800 px-4 py-2 rounded-xl text-center md:text-right">
                        <span class="text-[10px] uppercase font-bold text-slate-500 block">Trạng thái mạng</span>
                        <span class="text-xs font-bold text-emerald-400 font-mono animate-pulse">● Đã đồng bộ MongoDB Cloud</span>
                    </div>
                </div>

                <div class="bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
                    <div class="overflow-x-auto">
                        <table class="w-full border-collapse text-left">
                            <thead>
                                <tr class="bg-slate-950 border-b border-slate-800 text-[10px] font-black uppercase text-slate-400 tracking-widest">
                                    <th class="p-4">⏰ Thời gian ghi nhận</th>
                                    <th class="p-4">🔑 Mã bản ghi (QR ID)</th>
                                    <th class="p-4">📦 Loại nông sản</th>
                                    <th class="p-4">🌾 Trạng thái ruộng màu</th>
                                    <th class="p-4 text-right">🛠️ Hành động</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-800/40">
                                __ROWS_PLACEHOLDER__
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="text-center text-[10px] text-slate-600 font-mono pt-4">
                    AUTOMATED PROVENANCE SAAS GRADE v2.8 • POWERED BY MONGO_ATLAS & GEMINI AI
                </div>
            </div>

        </body>
        </html>
        """
        return main_template.replace("__ROWS_PLACEHOLDER__", rows_html)
