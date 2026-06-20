import hashlib
import json
from datetime import datetime, timezone
from pydantic import BaseModel, Field

# -------------------------------------------------------------
# DTO (DATA TRANSFER OBJECT): KHÓA CHẶT BIÊN GIỚI DỮ LIỆU
# -------------------------------------------------------------
class ProvenanceRecord(BaseModel):
    """
    Hóa giải Nghi ngờ 12: Đóng đinh cấu trúc chứng chỉ VietGAP số.
    Mọi dữ liệu xuất ra siêu thị bắt buộc phải khít từng trường này.
    """
    record_id: str = Field(..., description="Mã băm độc bản của bản ghi minh chứng")
    timestamp: str = Field(..., description="Thời gian ghi nhận chuẩn ISO UTC+7")
    crop_type: str = Field(..., example="NGO_NGOT")
    crop_stage: str = Field(..., description="Giai đoạn sinh trưởng thực tế của cây")
    weather_telemetry: str = Field(..., description="Dữ liệu thời tiết API cào được tại thời điểm đó")
    ai_directive: str = Field(..., description="Lời dặn hành động gốc mà AI đã phát đi")
    verification_hash: str = Field(..., description="Chữ ký số kiểm tra tính toàn vẹn, chống sửa đổi dữ liệu")

# -------------------------------------------------------------
# CORE LOGIC: HỘP XÁM TỰ ĐỘNG SINH DẤU CHÂN SỐ
# -------------------------------------------------------------
class ProvenanceEngine:
    def __init__(self, storage_client=None):
        self.storage = storage_client

    def generate_immutable_hash(self, payload: dict) -> str:
        """
        Tạo ra mã băm SHA-256 từ dữ liệu gốc. 
        Nếu ai đó cố tình vào DB sửa một chữ, mã hash sẽ đổi ngay lập tức -> Phát hiện gian lận!
        """
        serialized_data = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(serialized_data.encode('utf-8')).hexdigest()

    def build_provenance_footprint(self, crop: str, stage: str, weather_text: str, ai_text: str) -> ProvenanceRecord:
        """
        Hộp xám sâu: Tự động gom dữ liệu thời gian thực để dệt thành chứng chỉ số
        """
        vn_time = datetime.now(timezone.utc).isoformat() # Chuẩn hóa thời gian toàn cầu
        
        # Payload thô dùng để sinh mỏ neo kiểm tra tính toàn vẹn
        raw_payload = {
            "crop_type": crop.upper(),
            "crop_stage": stage,
            "weather_telemetry": weather_text,
            "ai_directive": ai_text
        }
        
        v_hash = self.generate_immutable_hash(raw_payload)
        record_id = f"REC-{v_hash[:12].upper()}" # Tạo mã bản ghi ngắn gọn chuyên nghiệp
        
        # Ép dữ liệu vào khuôn Pydantic cứng trước khi nhả ra ngoài
        record = ProvenanceRecord(
            record_id=record_id,
            timestamp=vn_time,
            crop_type=crop.upper(),
            crop_stage=stage,
            weather_telemetry=weather_text,
            ai_directive=ai_text,
            verification_hash=v_hash
        )
        
        # Sau này sếp chỉ cần gọi lệnh lưu con record này vào MongoDB ở đây
        # if self.storage: self.storage.save_provenance(record.model_dump())
        
        return record

