import logging
import requests
import json
import re
import os
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# ==========================================================
# 🌐 GIỮ PORT ĐỂ RENDER WEB SERVICE KHÔNG BỊ DISCONNECT
# ==========================================================
web_app = Flask('')

@web_app.route('/')
def home():
    return "DVTShop Bot is running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host='0.0.0.0', port=port)

# Khởi chạy Web Server ở luồng phụ
Thread(target=run_web, daemon=True).start()

# ==========================================================
# ⚙️ CẤU HÌNH KEY (LẤY TỪ BIẾN MÔI TRƯỜNG VÀ DỰ PHÒNG)
# ==========================================================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8710398772:AAGMzDrXh1ZH5FjjTUy9gSPtBm52zyYFcug")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyDKAw4wp3HXJa8Q6TW4tyFfuK1AghC4ziY")

# 🧠 NẠP KIẾN THỨC VÀ TÍNH CÁCH CHO BOT DVT SHOP
SYSTEM_PROMPT = """
[STRICT INSTRUCTION: RESPOND ONLY WITH THE FINAL REPLY. DO NOT INCLUDE THINKING, DRAFTS, OUTLINES, OR NOTES.]

Bạn là Trợ lý AI bán hàng và hỗ trợ kỹ thuật thông minh của cửa hàng DVTShop (DVT Shop HCM).
Phong cách giao tiếp: Thân thiện, vui vẻ, lịch sự, am hiểu kỹ thuật TV Box và thiết bị điện tử.

Thông tin cửa hàng & Sản phẩm DVTShop:
- Chuyên doanh: Android TV Box custom ROM mượt mà (IP952, FPT H650, Ubox, Mi Box...), linh kiện điện tử, phụ kiện tivi, máy nhổ lông vịt.
- Đặc điểm ROM DVTShop: Đã mã hóa bảo mật, tự động cập nhật ứng dụng, xem truyền hình/phim mượt không quảng cáo, giao diện dễ dùng cho người già/trẻ em.
- Hotline / Zalo hỗ trợ: 0968.862.84
- Khi khách hỏi mua hàng hoặc hỏi địa chỉ: Hãy chào hỏi nồng nhiệt, báo giá tham khảo và mời khách nhắn Zalo hoặc để lại SĐT để shop lên đơn.
- Khi khách báo lỗi kỹ thuật (Box bị treo, mất app, lỗi mạng): Hãy hướng dẫn kiểm tra dây nguồn, cắm lại dây LAN/Wifi, khởi động lại Box hoặc gửi Android ID cho shop check.

BẮT BỘC: Chỉ xuất ra duy nhất câu trả lời cuối cùng gửi cho khách hàng. Không phân tích, không lập dàn ý tiếng Anh hay tiếng Việt.
"""

WORKING_MODEL = None

def clean_ai_response(text):
    """Hàm dọn sạch 100% dàn ý, suy nghĩ, prompt nháp của AI"""
    text = re.sub(r'<thought>.*?</thought>', '', text, flags=re.DOTALL)
    
    if "User Input:" in text or "Persona:" in text or "Greeting:" in text:
        matches = re.findall(r'"([^"]*)"', text, flags=re.DOTALL)
        if matches:
            longest_match = max(matches, key=len)
            if len(longest_match) > 20:
                return longest_match.strip()
        
        lines = text.strip().split('\n')
        clean_lines = [
            l for l in lines 
            if not any(k in l for k in ['User Input:', 'Persona:', 'Tone:', 'Key Info:', 'Goal:', 'Introduction:', 'Capability:', 'Respond only', 'Include thinking', 'Draft', 'Greeting'])
        ]
        text = '\n'.join(clean_lines).strip()
        
    return text

def call_gemini_api(user_message):
    global WORKING_MODEL
    headers = {'Content-Type': 'application/json'}
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": user_message}]}]
    }

    if WORKING_MODEL:
        url = f"https://generativelanguage.googleapis.com/v1beta/{WORKING_MODEL}:generateContent?key={GEMINI_API_KEY}"
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            raw_reply = data['candidates'][0]['content']['parts'][0]['text']
            return clean_ai_response(raw_reply)
        else:
            WORKING_MODEL = None

    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    res = requests.get(list_url, timeout=15)
    
    if res.status_code != 200:
        raise Exception(f"Lỗi lấy danh sách Model (HTTP {res.status_code}): {res.text}")
        
    models_data = res.json().get('models', [])
    
    for m in models_data:
        if 'generateContent' in m.get('supportedGenerationMethods', []):
            model_name = m['name']
            url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={GEMINI_API_KEY}"
            
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    WORKING_MODEL = model_name
                    print(f"[SUCCESS] Đã kết nối qua Model: {model_name}")
                    raw_reply = data['candidates'][0]['content']['parts'][0]['text']
                    return clean_ai_response(raw_reply)
            except Exception:
                continue
                
    raise Exception("Không tìm thấy Model nào phản hồi!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_name = update.effective_user.first_name

    print(f"[+] Chat từ [{user_name}]: {user_text}")

    try:
        bot_reply = call_gemini_api(user_text)
        await update.message.reply_text(bot_reply)
    except Exception as e:
        print(f"[-] Lỗi AI Chi Tiết: {str(e)}")
        await update.message.reply_text("Shop đang bận một chút, bác vui lòng nhắn Zalo 0968.862.84 để được hỗ trợ ngay nhé!")

if __name__ == "__main__":
    print("==========================================")
    print("    BOT AI DVT SHOP ĐÃ BẬT - SẴN SÀNG!    ")
    print("==========================================")
    
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling()
