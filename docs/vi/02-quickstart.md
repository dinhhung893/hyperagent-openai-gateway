[![English](https://img.shields.io/badge/lang-English-8b949e?style=flat-square)](../en/02-quickstart.md) [![Tiếng Việt](https://img.shields.io/badge/lang-Ti%E1%BA%BFng%20Vi%E1%BB%87t-1f6feb?style=flat-square)](../vi/02-quickstart.md) · [🏠 README](../../README.vi.md) · [📚 Mục lục](00-index.md)

# Bắt đầu nhanh

Công cụ gói gọn trong một lệnh — `hyperagent-gateway` (bí danh **`hga`**). Cài xong,
chỉ hai lệnh là chạy.

## 1. Cài đặt

**Điều kiện tiên quyết:** Python 3.11+ (trừ Docker). Trên **Windows**, cài Python từ
[python.org](https://www.python.org/downloads/) và tick *"Add python.exe to PATH"*
(sẽ có lệnh `py`).

**Cách phổ quát (Windows / macOS / Linux):**

```bash
pip install git+https://github.com/dinhhung893/hyperagent-openai-gateway
# Windows PowerShell, nếu pip không có trên PATH:
py -m pip install git+https://github.com/dinhhung893/hyperagent-openai-gateway
```

Sẽ có lệnh `hyperagent-gateway` (bí danh `hga`). Nếu shell không thấy lệnh, dùng
`python -m gateway.cli …` (Windows: `py -m gateway.cli …`) là tương đương chính xác.

**Các cách khác**

| Cách | macOS / Linux | Windows (PowerShell) |
| --- | --- | --- |
| pipx | `pipx install git+…` | `py -m pip install --user pipx; py -m pipx ensurepath` → mở lại → `pipx install git+…` |
| uv | `uvx --from git+… hyperagent-gateway serve` | `irm https://astral.sh/uv/install.ps1 \| iex` → `uvx …` |
| Docker | `docker compose up -d --build` | `docker compose up -d --build` |
| 1 dòng | `curl -fsSL …/install.sh \| bash` | `irm …/install.ps1 \| iex` |

> **Windows/PowerShell:** `curl` là bí danh của `Invoke-WebRequest` và KHÔNG có
> `bash`; dòng `curl … | bash` chỉ cho macOS/Linux/WSL — hãy dùng `install.ps1`.

> Bên dưới, nếu Windows không tìm thấy `hga`, thay `hga` bằng `py -m gateway.cli`.

## 2. Thử ngoại tuyến (không cần tài khoản)

```bash
hga serve --upstream mock
# ở cửa sổ khác:
curl http://localhost:8000/v1/chat/completions -H "content-type: application/json" \
  -d '{"model":"agent_default","messages":[{"role":"user","content":"Xin chào"}]}'
```

## 3. Kết nối Hyperagent thật

```bash
hga login                 # đăng nhập trình duyệt một lần; lưu token tự gia hạn
hga agents                # xác nhận agent hiện ra
hga serve                 # chạy tại http://localhost:8000/v1
```

`hga login` mở trình duyệt (Google/Apple/Microsoft) và ghi token vào
`~/.hyperagent-gateway/tokens.json`. Trên máy chủ không có trình duyệt, dùng luồng
hai bước — xem [Triển khai](06-deployment.md#oauth-mot-lan-tren-may-chu).

> Cần ít nhất một **named agent** trong Hyperagent (máy chủ MCP chỉ mở thread trên
> named agent). Nếu `hga agents` rỗng, hãy tạo một cái trong ứng dụng Hyperagent.

## 4. Cấu hình bằng `.env` (tùy chọn, khuyến nghị)

Thay vì gõ dòng env dài, chạy `hga init` (hỏi-đáp) hoặc thả một file `.env`:

```bash
# ~/.hyperagent-gateway/.env  (hoặc ./.env ở thư mục làm việc)
GATEWAY_UPSTREAM=mcp
SHIM_API_KEYS=sk-khoacuatoi
GATEWAY_PORT=8000
```

Thứ tự ưu tiên: cờ CLI → biến môi trường → `.env` (thư mục hiện tại, rồi thư mục
home) → mặc định.

## 5. Trỏ phần mềm vào cổng

**Thư viện OpenAI (Python)**
```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="sk-khoacuatoi")
print(client.chat.completions.create(
    model="hyperagent-default",
    messages=[{"role":"user","content":"Tóm tắt tin AI hôm nay"}]).choices[0].message.content)
```

**Cursor / Continue / LibreChat / OpenWebUI:** Base URL `http://localhost:8000/v1`,
API key = một trong các `SHIM_API_KEYS`, model = một agent id từ `hga agents`.

## Xử lý sự cố

| Hiện tượng | Cách sửa |
| --- | --- |
| `hga agents` rỗng | Tạo một **named agent** trong Hyperagent. |
| `401 Invalid API key` | Khóa client không có trong `SHIM_API_KEYS`. |
| "No Hyperagent OAuth token" | Chạy `hga login` (hoặc đặt `HYPERAGENT_TOKEN_FILE`). |
| Lần gọi thật đầu tiên chậm | Bình thường — chạy cả agent. Tăng `GATEWAY_RUN_TIMEOUT` nếu cần. |
| Không rõ lỗi gì | Chạy `hga doctor`. |

Tiếp theo: [Kiến trúc](03-architecture.md) · [Tham chiếu API](04-api-reference.md).
