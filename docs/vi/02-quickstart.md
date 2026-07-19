[![English](https://img.shields.io/badge/lang-English-8b949e?style=flat-square)](../en/02-quickstart.md) [![Tiếng Việt](https://img.shields.io/badge/lang-Ti%E1%BA%BFng%20Vi%E1%BB%87t-1f6feb?style=flat-square)](../vi/02-quickstart.md) · [🏠 README](../../README.vi.md) · [📚 Mục lục](00-index.md)

# Bắt đầu nhanh

Có hai cách chạy: **ngoại tuyến (mock)** để thấy nó hoạt động trong 30 giây, rồi
**chạy thật** với Hyperagent.

## 0. Yêu cầu

- Python **3.11+** (`python3.11 --version`)
- Một cửa sổ dòng lệnh. Chế độ mock không cần database hay tài khoản.

## 1. Cài đặt

```bash
git clone https://github.com/dinhhung893/hyperagent-openai-gateway.git
cd hyperagent-openai-gateway
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Chạy ngoại tuyến (thượng nguồn mock)

Thượng nguồn **mock** giả lập Hyperagent để bạn thử bề mặt OpenAI mà không cần
tài khoản:

```bash
GATEWAY_UPSTREAM=mock uvicorn gateway.app:app --port 8000
```

Ở cửa sổ khác:

```bash
curl http://localhost:8000/v1/models
# → {"object":"list","data":[{"id":"agent_default",...},{"id":"agent_research",...}]}

curl http://localhost:8000/v1/chat/completions -H "content-type: application/json" \
  -d '{"model":"agent_default","messages":[{"role":"user","content":"Xin chào"}]}'
# → một chat.completion lặp lại tin nhắn của bạn
```

Vậy là cổng chạy được. Giờ kết nối bản thật.

## 3. Cấp quyền Hyperagent (một lần)

Hyperagent **không có API key** — bạn đăng nhập qua trình duyệt một lần, cổng sẽ
lưu token có thể tự gia hạn.

```bash
python tools/oauth_login.py --out ~/.hyperagent-gateway/tokens.json
```

Lệnh này mở trình duyệt, bạn đăng nhập (Google/Apple/Microsoft) và bấm chấp thuận.
Gói token được ghi vào `~/.hyperagent-gateway/tokens.json` (giữ bí mật).

> Trên máy chủ không có trình duyệt, dùng `tools/oauth_remote.py` — xem
> [Triển khai](06-deployment.md#oauth-mot-lan-tren-may-chu).

**Bạn cũng cần ít nhất một named agent** trong tài khoản Hyperagent (máy chủ MCP
chỉ mở thread trên named agent). Hãy tạo một cái trong ứng dụng Hyperagent; nên
chọn agent được tinh chỉnh để trả lời yêu cầu API (repo này dùng agent tên
**API Bridge**).

## 4. Chạy với Hyperagent thật

```bash
GATEWAY_UPSTREAM=mcp \
SHIM_API_KEYS=sk-khoacuatoi \
HYPERAGENT_TOKEN_FILE=~/.hyperagent-gateway/tokens.json \
uvicorn gateway.app:app --port 8000
```

- `SHIM_API_KEYS` = khóa mà client phải gửi (giống khóa OpenAI). Chỉ để trống khi
  dev cục bộ.

Kiểm tra agent thật xuất hiện:

```bash
curl http://localhost:8000/v1/models -H "authorization: Bearer sk-khoacuatoi"
```

Gửi một câu chat thật (chạy cả một agent — có thể mất vài chục giây):

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "authorization: Bearer sk-khoacuatoi" -H "content-type: application/json" \
  -d '{"model":"hyperagent-default","messages":[{"role":"user","content":"Thủ đô Việt Nam là gì? Một từ."}]}'
```

## 5. Trỏ phần mềm yêu thích vào cổng

**Thư viện OpenAI (Python)**
```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="sk-khoacuatoi")
print(client.chat.completions.create(
    model="hyperagent-default",
    messages=[{"role":"user","content":"Tóm tắt tin AI hôm nay"}]).choices[0].message.content)
```

**Cursor / Continue / LibreChat / OpenWebUI**
- Base URL OpenAI: `http://localhost:8000/v1`
- API key: `sk-khoacuatoi`
- Model: một agent id từ `/v1/models` (hoặc `hyperagent-default`)

## Xử lý sự cố

| Hiện tượng | Nguyên nhân & cách sửa |
| --- | --- |
| `/v1/models` trả danh sách rỗng | Tài khoản chưa có **named agent**. Tạo một cái trong Hyperagent. |
| `401 Invalid API key` | Khóa của client không nằm trong `SHIM_API_KEYS`. |
| `No Hyperagent OAuth token` | Chạy `tools/oauth_login.py` và đặt `HYPERAGENT_TOKEN_FILE`. |
| Lần gọi thật đầu tiên chậm | Bình thường — agent chạy cả pipeline. Tăng `GATEWAY_RUN_TIMEOUT` nếu cần. |
| `504 upstream_timeout` | Lượt chạy lâu hơn `GATEWAY_RUN_TIMEOUT` (mặc định 600s). Hãy tăng lên. |

Tiếp theo: [Kiến trúc](03-architecture.md) hoặc [Tham chiếu API](04-api-reference.md).
