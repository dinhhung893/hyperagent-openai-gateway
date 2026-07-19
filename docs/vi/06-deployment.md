[![English](https://img.shields.io/badge/lang-English-8b949e?style=flat-square)](../en/06-deployment.md) [![Tiếng Việt](https://img.shields.io/badge/lang-Ti%E1%BA%BFng%20Vi%E1%BB%87t-1f6feb?style=flat-square)](../vi/06-deployment.md) · [🏠 README](../../README.vi.md) · [📚 Mục lục](00-index.md)

# Triển khai & bảo mật

## Docker

```bash
docker build -t hyperagent-openai-gateway .
docker run -d --name gateway -p 8000:8000 \
  -e GATEWAY_UPSTREAM=mcp \
  -e SHIM_API_KEYS=sk-prod-key \
  -v ~/.hyperagent-gateway:/root/.hyperagent-gateway \
  hyperagent-openai-gateway
```

Gắn một volume để gói token OAuth và trạng thái cục bộ còn lại sau khi khởi động
lại.

## Sau reverse proxy (HTTPS)

Chạy cổng ở `127.0.0.1:8000` và đặt Nginx/Caddy phía trước để lo TLS.

Ví dụ Caddy:
```
api.example.com {
  reverse_proxy 127.0.0.1:8000
}
```
Nginx: `proxy_pass http://127.0.0.1:8000;` và đặt `proxy_buffering off;` để
streaming SSE chảy qua được.

<a id="oauth-mot-lan-tren-may-chu"></a>
## OAuth một lần trên máy chủ

Nếu máy chủ không có trình duyệt, dùng trợ giúp hai bước:

```bash
# Trên máy chủ: đăng ký + lấy URL cấp quyền
python tools/oauth_remote.py start --redirect https://CALLBACK_CUA_BAN/cb
# Mở URL in ra bằng BẤT KỲ trình duyệt nào, chấp thuận, chép ?code=… từ URL chuyển hướng
python tools/oauth_remote.py finish --callback-url "https://CALLBACK_CUA_BAN/cb?code=...&state=..."
```
Lệnh này ghi `~/.hyperagent-gateway/tokens.json` kèm refresh token; sau đó cổng tự
xoay vòng token.

## Đa người dùng (nhiều người, một cổng)

Tạo một file khóa và trỏ `GATEWAY_KEYS_FILE` vào nó:

```json
[
  {"api_key":"sk-an","token_file":"~/.hyperagent-gateway/an.json","default_agent":"<agentId>","disabled_tools":["shell"],"label":"an"},
  {"api_key":"sk-binh","token_file":"~/.hyperagent-gateway/binh.json","label":"binh"}
]
```

- Mỗi người chạy trợ giúp OAuth một lần để tạo `token_file` riêng.
- Khóa lạ nhận `401`. Mỗi khóa hành xử đúng như chính người dùng Hyperagent của nó.
- `disabled_tools` và `default_agent` theo từng khóa được thực thi.

## Danh sách kiểm tra bảo mật

- **Không bao giờ commit bí mật.** `tokens.json`, `.env`, và trạng thái cục bộ đều
  bị gitignore; giữ file token ở `chmod 600`.
- **Dùng `SHIM_API_KEYS` mạnh** và xoay vòng; coi chúng như khóa OpenAI.
- **Khóa các công cụ nguy hiểm** cho khóa dùng chung:
  `GATEWAY_DISABLED_TOOLS=shell,write_file`.
- **Kết thúc TLS** ở proxy; đừng phơi HTTP trần ra công khai.
- **Nhớ rằng token đại diện cho người dùng** — lộ gói token = lộ toàn quyền tài
  khoản Hyperagent đó. Ở môi trường thật, lưu trong trình quản lý bí mật.

## Ghi chú về mở rộng

- Lượt chạy dài (vài giây). Dùng timeout client rộng rãi và một trình quản lý tiến
  trình (systemd, chính sách restart của Docker) hoặc nhiều worker uvicorn.
- `GATEWAY_RUN_TIMEOUT` giới hạn thời gian cổng chờ một lượt chạy.
