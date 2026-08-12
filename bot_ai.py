import os
import re
import requests
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# ==========================================================
# 🌐 GIỮ PORT CHO RENDER WEB SERVICE
# ==========================================================
web_app = Flask('')

@web_app.route('/')
def home():
    return "DVTShop Bot is running 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    web_app.run(host='0.0.0.0', port=port)

Thread(target=run_web, daemon=True).start()

# ==========================================================
# ⚙️ CẤU HÌNH KEY & PROMPT
# ==========================================================
TELEGRAM_BOT_TOKEN = "8710398772:AAHAcqcxjkzlJVlv4enzxD5r9rmc-TrM3hk"
GEMINI_API_KEY = "AQ.Ab8RN6LsUpjnrZxkTRZQlzeInRbUL6X_4cQ45qZzfgsH-6u7EA"

SYSTEM_PROMPT = """
Bạn là Trợ lý AI bán hàng và hỗ trợ kỹ thuật thông minh của cửa hàng DVTShop (DVT Shop HCM).
Phong cách giao tiếp: Thân thiện, vui vẻ, lịch sự, am hiểu kỹ thuật TV Box và thiết bị điện tử.

Thông tin cửa hàng & Sản phẩm DVTShop:
- Chuyên doanh: Android TV Box custom ROM mượt mà (IP952, FPT H650, Ubox, Mi Box...), linh kiện điện tử, phụ kiện tivi, máy nhổ lông vịt.
- Đặc điểm ROM DVTShop: Đã mã hóa bảo mật, tự động cập nhật ứng dụng, xem truyền hình/phim mượt không quảng cáo, giao diện dễ dùng cho người già/trẻ em.
- Hotline / Zalo hỗ trợ: 0968.862.84
- Khi khách hỏi mua hàng hoặc hỏi địa chỉ: Hãy chào hỏi nồng nhiệt, báo giá tham khảo và mời khách nhắn Zalo hoặc để lại SĐT để shop lên đơn.
- Khi khách báo lỗi kỹ thuật (Box bị treo, mất app, lỗi mạng): Hãy hướng dẫn kiểm tra dây nguồn, cắm lại dây LAN/Wifi, khởi động lại Box hoặc gửi Android ID cho shop check.

BẮT BỘC: Chỉ xuất ra duy nhất câu trả lời cuối cùng gửi cho khách hàng. Không phân tích, không lập dàn ý.
"""

def clean_ai_response(text):
    text = re.sub(r'<thought>.*?</thought>', '', text, flags=re.DOTALL)
    return text.strip()

def call_gemini_api(user_message):
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{
            "parts": [{"text": f"{SYSTEM_PROMPT}\n\nKhách hỏi: {user_message}"}]
        }]
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    response = requests.post(url, headers=headers, json=payload, timeout=20)
    
    if response.status_code == 200:
        data = response.json()
        raw_reply = data['candidates'][0]['content']['parts'][0]['text']
        return clean_ai_response(raw_reply)
    else:
        # In chính xác nguyên nhân lỗi do Google trả về ra log
        print(f"[ERR GOOGLE {response.status_code}]: {response.text}")
        raise Exception(f"Lỗi API Google: {response.status_code}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_name = update.effective_user.first_name

    print(f"[+] Chat từ [{user_name}]: {user_text}")

    try:
        bot_reply = call_gemini_api(user_text)
        await update.message.reply_text(bot_reply)
    except Exception as e:
        print(f"[-] Lỗi chi tiết: {str(e)}")
        await update.message.reply_text("Shop đang bận một chút, bác vui lòng nhắn Zalo 0968.862.84 để được hỗ trợ ngay nhé!")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.run_polling(drop_pending_updates=True)
