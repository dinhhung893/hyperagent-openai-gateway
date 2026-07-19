<!-- LANGUAGE SWITCH -->
[![English](https://img.shields.io/badge/README-English-8b949e?style=for-the-badge)](README.md) [![Tiếng Việt](https://img.shields.io/badge/README-Ti%E1%BA%BFng%20Vi%E1%BB%87t-1f6feb?style=for-the-badge)](README.vi.md)

# Cổng API tương thích OpenAI cho Hyperagent

![Python](https://img.shields.io/badge/Python-3.11+-3776ab?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)
![Tests](https://img.shields.io/badge/tests-46%20passing-3fb950)
![Upstream](https://img.shields.io/badge/upstream-Hyperagent%20MCP-7c5cff)

**Biến Hyperagent.com thành một backend nói "tiếng OpenAI".** Bạn trỏ bất kỳ phần
mềm tương thích OpenAI nào (thư viện `openai`, Cursor, Continue, LibreChat,
LangChain, …) vào cổng này và gọi đúng các endpoint quen thuộc —
`/v1/chat/completions`, `/v1/models`, `/v1/responses`, … Cổng sẽ dịch mỗi yêu cầu
sang thao tác Hyperagent và trả kết quả đúng định dạng OpenAI (kể cả streaming).

> **Một câu gọn:** code OpenAI cũ của bạn vẫn chạy nguyên, nhưng "mô hình" trả
> lời thực chất là một **agent** Hyperagent đầy đủ — biết tìm web, chạy code,
> điều khiển trình duyệt, tạo ảnh/âm thanh và gọi các tích hợp của bạn.

📚 **Tài liệu đầy đủ:** [Tiếng Việt](docs/vi/00-index.md) ·
[English docs](docs/en/00-index.md)

---

## Mục lục

- [Đây là cái gì?](#đây-là-cái-gì)
- [Hoạt động thế nào?](#hoạt-động-thế-nào)
- [Bắt đầu nhanh](#bắt-đầu-nhanh)
- [Kết nối phần mềm của bạn](#kết-nối-phần-mềm-của-bạn)
- [Các endpoint hỗ trợ](#các-endpoint-hỗ-trợ)
- [Cầu nối công cụ](#cầu-nối-công-cụ-shell-write-web-)
- [Đa người dùng](#đa-người-dùng)
- [Cấu hình](#cấu-hình)
- [Triển khai](#triển-khai)
- [Kiểm thử](#kiểm-thử)
- [Cấu trúc dự án](#cấu-trúc-dự-án)
- [Repo này được phát triển ra sao](#repo-này-được-phát-triển-ra-sao)
- [Giới hạn](#giới-hạn)
- [Câu hỏi thường gặp](#câu-hỏi-thường-gặp)
- [Giấy phép](#giấy-phép)

---

## Đây là cái gì?

**API của OpenAI** gần như là một chuẩn chung: rất nhiều phần mềm đã biết cách
"nói chuyện" với nó. **Hyperagent.com** là nền tảng nơi các *agent* AI làm việc
thật trong các *thread* (luồng) bền bỉ: nghiên cứu, viết code, điều khiển trình
duyệt, tạo media, làm việc với file và tích hợp. Cánh cửa lập trình công khai duy
nhất của Hyperagent là một **máy chủ MCP** (Model Context Protocol) — chứ không
phải một API kiểu OpenAI.

Dự án này là **bộ chuyển đổi** giữa hai thế giới đó. Hãy hình dung nó như một
**ổ cắm điện đa năng**: thiết bị của bạn (phần mềm OpenAI) cắm vào y như cũ, còn
phía sau tường, điện thực ra đến từ Hyperagent.

**Dành cho ai?**
- Người đã có sẵn ứng dụng dùng OpenAI và muốn đổi "bộ não" sang agent mà **không
  phải viết lại code**.
- Các công cụ chỉ biết "tiếng OpenAI" (IDE, giao diện chat) nhưng muốn dùng sức
  mạnh của Hyperagent.

Mới với các thuật ngữ này? Bắt đầu ở [Tổng quan & khái niệm](docs/vi/01-overview.md).

## Hoạt động thế nào?

```text
Phần mềm tương thích OpenAI  (Cursor, Continue, LibreChat, thư viện openai, …)
        │  HTTP:  POST /v1/chat/completions   (Authorization: Bearer <khóa cổng>)
        ▼
┌───────────────────────────────────────────────┐
│  Cổng (FastAPI)                                │
│  • Xác thực: khóa cổng → một danh tính Hyperagent │
│  • Dịch: OpenAI  ⇄  thao tác thread Hyperagent │
│  • UpstreamAdapter:  MCP (thật)  |  Mock (thử) │
└───────────────────────────────────────────────┘
        │  MCP JSON-RPC 2.0 qua HTTPS  (token Bearer OAuth 2.1)
        ▼
Máy chủ MCP Hyperagent   https://hyperagent.com/api/mcp
        │  list_agents · create_thread · get_thread (poll) · send_message · …
        ▼
Agent Hyperagent của bạn xử lý yêu cầu từ đầu đến cuối
(tìm web, trình duyệt, shell, file, ảnh/âm thanh, tích hợp)
```

Những ý chính:
- **`model` = một agent Hyperagent.** `GET /v1/models` liệt kê các agent của bạn;
  chọn một cái làm `model`, hoặc dùng bí danh `hyperagent-default`.
- **Một yêu cầu = một lượt chạy thread.** Hyperagent chạy nền, nên cổng sẽ **hỏi
  liên tục (poll)** cho tới khi có kết quả.
- **Streaming là mô phỏng.** Hyperagent không "nhả" từng token, nên cổng biến các
  lần poll thành các mẩu SSE chuẩn OpenAI.
- **Thiết kế phi trạng thái (stateless).** Mỗi lần gọi là tự chứa đầy đủ (xem
  [Kiến trúc](docs/vi/03-architecture.md)); cổng không dựa vào trí nhớ chập chờn
  của thượng nguồn.

## Bắt đầu nhanh

Cần Python 3.11 trở lên.

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**Thử ngay khi chưa có tài khoản** — dùng thượng nguồn *mock* có sẵn:

```bash
GATEWAY_UPSTREAM=mock uvicorn gateway.app:app --port 8000
curl http://localhost:8000/v1/chat/completions -H "content-type: application/json" \
  -d '{"model":"agent_default","messages":[{"role":"user","content":"Xin chào"}]}'
```

**Dùng Hyperagent thật** — cần đăng nhập OAuth một lần:

```bash
python tools/oauth_login.py --out ~/.hyperagent-gateway/tokens.json   # một lần, qua trình duyệt
GATEWAY_UPSTREAM=mcp SHIM_API_KEYS=sk-khoacuatoi \
  uvicorn gateway.app:app --port 8000
```

Hướng dẫn từng bước (kèm kết quả từng lệnh): [Bắt đầu nhanh](docs/vi/02-quickstart.md).

> **Lưu ý:** tài khoản Hyperagent của bạn cần có ít nhất một **named agent** (máy
> chủ MCP chỉ mở thread trên named agent). Repo này được dựng với agent tên là
> **API Bridge**.

## Kết nối phần mềm của bạn

**Thư viện OpenAI (Python)**

```python
from openai import OpenAI
client = OpenAI(base_url="http://localhost:8000/v1", api_key="sk-khoacuatoi")
print(client.models.list())                     # các agent Hyperagent của bạn
r = client.chat.completions.create(
    model="hyperagent-default",
    messages=[{"role": "user", "content": "Nghiên cứu X và tóm tắt giúp tôi"}],
)
print(r.choices[0].message.content)
```

**curl**

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "authorization: Bearer sk-khoacuatoi" -H "content-type: application/json" \
  -d '{"model":"hyperagent-default","messages":[{"role":"user","content":"Xin chào"}],"stream":true}'
```

**Cursor / Continue / LibreChat / OpenWebUI:** đặt **Base URL** OpenAI là
`http://localhost:8000/v1`, **API key** là một trong các `SHIM_API_KEYS`, và
**model** là một agent id lấy từ `GET /v1/models`.

## Các endpoint hỗ trợ

| Endpoint | Trạng thái |
| --- | --- |
| `GET /v1/models`, `/v1/models/{id}` | ✅ liệt kê agent Hyperagent |
| `POST /v1/chat/completions` (stream + non-stream) | ✅ |
| `POST /v1/responses` (+ chạy nền, hủy, input_items, chuỗi có nhớ) | ✅ |
| `GET /v1/tools` + ép `tool_choice` | ✅ cầu nối công cụ |
| `POST /v1/completions` (kiểu cũ) | ✅ |
| `POST /v1/images/generations`, `/v1/images/edits` | ✅ URL tải được thật |
| `POST /v1/audio/speech`, `/transcriptions`, `/translations` | ✅ |
| `POST /v1/files`, `GET/DELETE /v1/files/{id}`, `/content` | ✅ + đính kèm vào chat |
| `POST /v1/embeddings` | ✅ bản dự phòng cục bộ (hoặc `501` nếu tắt) |
| `POST /v1/moderations` | ✅ heuristic |

Hành vi từng tham số: [Tham chiếu API](docs/vi/04-api-reference.md).

## Cầu nối công cụ (Shell, Write, web, …)

Agent Hyperagent có một "hộp đồ nghề" phong phú (shell/bash, đọc/ghi file, tìm
web, trình duyệt, ảnh/video/âm thanh, bảng, tài liệu, bản đồ, tích hợp). Cổng
phơi bày tất cả qua cơ chế `tools` / `tool_calls` chuẩn OpenAI, theo 3 chế độ:

- **Quan sát** — hoạt động công cụ của agent hiện ra dưới dạng `tool_calls` trong
  câu trả lời.
- **Chỉ định** — ép dùng một công cụ bằng `tool_choice`.
- **Chạy trực tiếp** — một "tool-runner" chạy thẳng công cụ (ví dụ lệnh shell) và
  trả kết quả.

`GET /v1/tools` trả về toàn bộ danh mục. Chi tiết + ví dụ:
[Cầu nối công cụ](docs/vi/05-tool-bridge.md).

## Đa người dùng

Một cổng có thể phục vụ nhiều người dùng Hyperagent. Ánh xạ mỗi API key sang một
danh tính + chính sách riêng qua `GATEWAY_KEYS_FILE`:

```json
[{"api_key":"sk-an","token_file":"~/.hyperagent-gateway/an.json","disabled_tools":["shell"]},
 {"api_key":"sk-binh","token_file":"~/.hyperagent-gateway/binh.json"}]
```

Mỗi người đăng nhập một lần bằng `tools/oauth_login.py`. Xem
[Triển khai & bảo mật](docs/vi/06-deployment.md).

## Cấu hình

| Biến | Mặc định | Ý nghĩa |
| --- | --- | --- |
| `GATEWAY_UPSTREAM` | `mcp` | `mcp` (thật) hoặc `mock` (ngoại tuyến) |
| `HYPERAGENT_MCP_URL` | `https://hyperagent.com/api/mcp` | endpoint thượng nguồn |
| `HYPERAGENT_TOKEN_FILE` | `~/.hyperagent-gateway/tokens.json` | gói token OAuth |
| `SHIM_API_KEYS` | (rỗng = chế độ dev) | danh sách khóa client, phân tách bằng dấu phẩy |
| `GATEWAY_KEYS_FILE` | (không) | bản đồ danh tính đa người dùng (JSON) |
| `GATEWAY_DEFAULT_AGENT` | (agent đầu tiên) | agent cho `hyperagent-default` |
| `GATEWAY_EXEC_MODE` | `roundtrip` | chế độ tool-runner: `roundtrip` hoặc `auto` |
| `GATEWAY_DISABLED_TOOLS` | (không) | ẩn công cụ, vd `shell,write_file` |
| `GATEWAY_EMBEDDINGS` | `fallback` | `fallback` hoặc `off` |
| `GATEWAY_POLL_INTERVAL` / `GATEWAY_RUN_TIMEOUT` | `1.0` / `600` | poll |

## Triển khai

```bash
docker build -t hyperagent-openai-gateway .
docker run -p 8000:8000 -e GATEWAY_UPSTREAM=mcp \
  -v ~/.hyperagent-gateway:/root/.hyperagent-gateway hyperagent-openai-gateway
```

Hướng dẫn đầy đủ (VPS, reverse proxy, HTTPS, quản lý bí mật):
[Triển khai](docs/vi/06-deployment.md).

## Kiểm thử

```bash
python3.11 -m pytest tests/ -q     # 46 test: unit + API qua ASGI + OpenAI SDK
```

## Cấu trúc dự án

```text
gateway/            App FastAPI + lớp dịch + adapter thượng nguồn
  app.py            toàn bộ route HTTP
  upstream/         mcp.py (thật) · mock.py (thử) · base.py · manager.py
  translate.py streaming.py toolbridge.py fallbacks.py media.py auth.py …
tools/              oauth_login.py, oauth_remote.py (trợ giúp OAuth một lần)
tests/              46 test (thượng nguồn mock + OpenAI SDK)
docs/en/  docs/vi/  tài liệu song ngữ
docs/product/       đặc tả kỹ thuật canonical (tiếng Anh)
Dockerfile  requirements.txt  pyproject.toml
```

## Repo này được phát triển ra sao

Repo được xây bằng **[repository-harness](https://github.com/hoangnb24/repository-harness)**,
một "hệ điều hành" nhẹ dành cho agent lập trình (phân loại yêu cầu, gói story, bản
ghi quyết định, ma trận kiểm thử). Các file đó (`AGENTS.md`, `docs/HARNESS*.md`,
`docs/product/`, `docs/decisions/`) mô tả *cách repo được xây*, không phải bản
thân sản phẩm. Nếu bạn chỉ muốn *dùng* cổng thì có thể bỏ qua chúng. Xem
[Đóng góp](docs/vi/09-contributing.md).

## Giới hạn

- **Độ trễ:** mỗi lần gọi chạy cả pipeline agent — tính bằng giây, không phải
  mili-giây.
- **Streaming là mô phỏng** (dựa trên poll), không phải nhả token thật.
- **Các núm chỉnh sinh văn bản** (`temperature`, `top_p`, `seed`) chỉ mang tính
  tương đối / không tác dụng.
- **Embeddings** dùng bản dự phòng cục bộ (không mang nghĩa ngữ nghĩa) trừ khi bạn
  cắm nhà cung cấp thật.
- **Xác thực** là OAuth theo từng người dùng (Hyperagent không có API key); cổng
  lưu và tự gia hạn token cho từng người.

## Câu hỏi thường gặp

Vài câu nhanh (đầy đủ: [FAQ](docs/vi/07-faq.md)):

- **Có phải sửa code OpenAI không?** Không — chỉ đổi `base_url` và `api_key`.
- **Truyền model nào?** Một agent id (`GET /v1/models`) hoặc `hyperagent-default`.
- **Có thật sự tương thích OpenAI không?** Có; thư viện `openai` chính thức chạy
  không cần sửa (đã kiểm thử).

## Giấy phép

Hiện chưa có file giấy phép. Cho tới khi thêm, mọi quyền thuộc về chủ repo. Mở
issue nếu bạn muốn một giấy phép cụ thể (ví dụ MIT).

---

<sub>Xây trên máy chủ MCP của Hyperagent. "OpenAI" là nhãn hiệu của OpenAI; dự án
này là lớp tương thích độc lập, không liên kết với OpenAI.</sub>
