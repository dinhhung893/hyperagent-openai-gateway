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

**Điều kiện tiên quyết:** Python 3.11+ (trừ cách Docker). Trên **Windows**, cài
Python từ [python.org](https://www.python.org/downloads/) và tick *"Add python.exe
to PATH"* — sẽ có sẵn lệnh `py`.

**1. Cài đặt — cách phổ quát** (chạy trên Windows, macOS, Linux):

```bash
pip install git+https://github.com/dinhhung893/hyperagent-openai-gateway
```
> Windows PowerShell: nếu không thấy `pip`, dùng `py -m pip install git+…`.

Sẽ có lệnh `hyperagent-gateway` (bí danh `hga`). Nếu shell không tìm thấy lệnh, cách
tương đương luôn chạy được: `python -m gateway.cli …` (Windows: `py -m gateway.cli …`).

<details><summary><b>Các cách cài khác</b> — pipx · uv · Docker · 1 dòng</summary>

| Cách | macOS / Linux | Windows (PowerShell) |
| --- | --- | --- |
| **pipx** | `pipx install git+…` | `py -m pip install --user pipx; py -m pipx ensurepath` → mở lại shell → `pipx install git+…` |
| **uv** | `uvx --from git+… hyperagent-gateway serve` | `irm https://astral.sh/uv/install.ps1 \| iex` → `uvx --from git+… hyperagent-gateway serve` |
| **Docker** | `docker compose up -d --build` | `docker compose up -d --build` |
| **1 dòng** | `curl -fsSL https://raw.githubusercontent.com/dinhhung893/hyperagent-openai-gateway/main/install.sh \| bash` | `irm https://raw.githubusercontent.com/dinhhung893/hyperagent-openai-gateway/main/install.ps1 \| iex` |

> **Lưu ý Windows:** trong PowerShell, `curl` là bí danh của `Invoke-WebRequest` và
> KHÔNG có `bash`, nên dòng `curl … \| bash` chỉ dành cho macOS/Linux/WSL. Hãy dùng
> `install.ps1` (qua `irm … \| iex`).
</details>

**2. Chạy — hai lệnh:**

```bash
hga login      # đăng nhập Hyperagent một lần (mở trình duyệt)
hga serve      # phục vụ tại http://localhost:8000/v1
```
> Windows nếu lệnh chưa có trên PATH: `py -m gateway.cli login` rồi `py -m gateway.cli serve`.

**Chỉ muốn thử?** Không cần tài khoản — chạy với mock:

```bash
hga serve --upstream mock          # hoặc:  py -m gateway.cli serve --upstream mock
```

> Tài khoản Hyperagent cần ít nhất một **named agent** (máy chủ MCP chỉ mở thread
> trên named agent). Kiểm tra bằng `hga agents`.

Hướng dẫn đầy đủ: [Bắt đầu nhanh](docs/vi/02-quickstart.md).

## Giao diện dòng lệnh (CLI)

`hyperagent-gateway` (bí danh `hga`):

| Lệnh | Chức năng |
| --- | --- |
| `hga init` | Ghi `~/.hyperagent-gateway/.env` (hỏi-đáp; `--yes` để lấy mặc định) |
| `hga login` | OAuth một lần (`--remote-start` / `--remote-finish` cho máy chủ không trình duyệt) |
| `hga serve` | Chạy gateway (`--port`, `--upstream mcp\|mock`, `--reload`, …) |
| `hga agents` | Liệt kê agent Hyperagent |
| `hga doctor` | Kiểm tra cấu hình + kết nối upstream |
| `hga quickstart` | `login` (nếu cần) rồi `serve` |

**Cấu hình tự nạp** theo thứ tự ưu tiên: cờ CLI → biến môi trường → `.env` (thư mục
hiện tại, rồi `~/.hyperagent-gateway/.env`) → mặc định. Nên chỉ cần một file `.env`,
khỏi gõ dòng env dài. (`uvicorn gateway.app:app` vẫn dùng được cho người thạo.)

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

**curl (macOS / Linux)**

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "authorization: Bearer sk-khoacuatoi" -H "content-type: application/json" \
  -d '{"model":"hyperagent-default","messages":[{"role":"user","content":"Xin chào"}]}'
```

**PowerShell (Windows)** — `curl` ở đây là `Invoke-WebRequest`, nên dùng:

```powershell
Invoke-RestMethod -Uri http://localhost:8000/v1/chat/completions -Method Post `
  -Headers @{ Authorization = "Bearer sk-khoacuatoi" } -ContentType 'application/json' `
  -Body '{"model":"hyperagent-default","messages":[{"role":"user","content":"Xin chào"}]}'
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

Docker Compose (khuyến nghị cho máy chủ) — đặt cấu hình trong `.env` và gói token ở
`./secrets/tokens.json`:

```bash
docker compose up -d --build
```

Hướng dẫn đầy đủ (VPS, reverse proxy, HTTPS, đa người dùng, OAuth headless):
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
Dockerfile  requirements.txt  pyproject.toml
```

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
