# backend/knowledge.py

AGRI_KNOWLEDGE_BASE = {
    "rau_muong": {
        "description": "Rau muống hè Văn Khê, chịu nhiệt tốt nhưng sợ mất nước.",
        "rules": [
            "Nếu nhiệt độ dự báo > 37°C: Bắt buộc tưới tràn vào gốc lúc 5h-6h sáng hoặc sau 5h chiều. Tuyệt đối không tưới trưa gây luộc rau.",
            "Nếu lượng mưa dự báo > 20mm (mưa lớn): Phải kiểm tra bờ bộc, khơi thông dòng chảy thoát nước rãnh luống lập tức để tránh thối gốc."
        ]
    },
    "muop_bi": {
        "description": "Mướp hương, bí xanh leo giàn vụ hè.",
        "rules": [
            "Nắng gắt kéo dài: Nhắc bà con dùng rơm rạ hoặc cỏ khô phủ kín gốc giữ ẩm, tránh ánh nắng thiêu đốt trực tiếp làm chết rễ tơ.",
            "Nguy cơ sốc nhiệt: Nếu đang nắng nóng gay gắt mà dự báo có mưa rào đột ngột, nhắc bà con phun phòng chế phẩm nấm đối kháng Trichoderma để tránh thối rễ, nứt quả."
        ]
    },
    "ngo_ngot": {
        "description": "Ngô ngọt vụ hè giai đoạn trổ cờ, phun râu thụ phấn.",
        "rules": [
            "Cháy hạt phấn: Nếu nhiệt độ > 38°C vào ban trưa, hạt phấn ngô sẽ bị chết, bắp bị lép hạt trơ lõi.",
            "Hành động khẩn cấp: Bật béc phun mưa áp lực cao tưới phun lên tán ngô vào lúc 9h-10h sáng để hạ nhiệt vi khí hậu, cứu hạt phấn thụ phấn thành công."
        ]
    }
}
