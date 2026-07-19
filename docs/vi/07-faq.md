[![English](https://img.shields.io/badge/lang-English-8b949e?style=flat-square)](../en/07-faq.md) [![Tiếng Việt](https://img.shields.io/badge/lang-Ti%E1%BA%BFng%20Vi%E1%BB%87t-1f6feb?style=flat-square)](../vi/07-faq.md) · [🏠 README](../../README.vi.md) · [📚 Mục lục](00-index.md)

# Câu hỏi thường gặp

### Người mới

**Tôi có phải sửa code không?** Không. Đặt `base_url` của client OpenAI trỏ vào
cổng và `api_key` là một trong các `SHIM_API_KEYS`. Còn lại giữ nguyên.

**Truyền gì vào `model`?** Một agent id lấy từ `GET /v1/models`, hoặc bí danh
`hyperagent-default`.

**Sao chậm hơn ChatGPT?** Vì mỗi lần gọi chạy cả một *agent* (có thể tìm web,
duyệt trang, chạy code), không phải một lần suy luận mô hình. Vài giây là bình
thường.

**Có cần biết MCP là gì không?** Không, để *dùng*. Có, nếu muốn hiểu bên trong —
xem [Thuật ngữ](08-glossary.md).

### Khi sử dụng

**Streaming có chạy không?** Có, dưới dạng SSE chuẩn — nhưng là *mô phỏng* bằng
poll, nên văn bản có thể đến theo vài mẩu thay vì từng token.

**Có tạo được ảnh/âm thanh không?** Có: `/v1/images/generations`,
`/v1/audio/speech`, … Ảnh trả về là URL công khai tải được.

**Model có chạy lệnh shell hay ghi file giúp tôi không?** Có, qua
[cầu nối công cụ](05-tool-bridge.md). Để an toàn, có thể tắt `shell`/`write_file`
theo từng khóa.

**Làm sao giữ trí nhớ hội thoại?** Với chat, cứ gửi đầy đủ `messages[]` mỗi lần
(chuẩn OpenAI). Với Responses API, dùng `previous_response_id` — cổng sẽ tái dựng
ngữ cảnh trước.

**Embeddings trông ngẫu nhiên / kém chất lượng.** Embeddings mặc định là *bản dự
phòng cục bộ* (hashing tất định, không mang nghĩa). Hãy cắm nhà cung cấp thật hoặc
đặt `GATEWAY_EMBEDDINGS=off`.

### Vận hành

**Bí mật của tôi lưu ở đâu?** Token OAuth ở `~/.hyperagent-gateway/tokens.json`
(giữ `chmod 600`); không bao giờ commit. Xem [Triển khai](06-deployment.md).

**Một cổng phục vụ cả nhóm được không?** Được — `GATEWAY_KEYS_FILE` ánh xạ mỗi
khóa sang danh tính + chính sách Hyperagent riêng.

**`/v1/models` rỗng.** Tài khoản chưa có **named agent**. Tạo một cái trong ứng
dụng Hyperagent.

**Một yêu cầu trả `504`.** Nó vượt `GATEWAY_RUN_TIMEOUT` (mặc định 600s). Hãy tăng
lên cho tác vụ agent dài.

### Tương thích & giới hạn

**Có 100% tương thích OpenAI không?** Các bề mặt cốt lõi thì có (SDK chính thức
chạy được). Vài tham số (`temperature`, `top_p`, `seed`, `logprobs`) không áp dụng
cho lượt chạy agent nên được chấp nhận-nhưng-bỏ-qua hoặc trả null. Xem
[Tham chiếu API](04-api-reference.md).

**Dự án này có liên kết với OpenAI không?** Không. Đây là lớp tương thích độc lập.

**Đâu là nguồn chân lý về hành vi?** Đặc tả canonical trong
[`docs/product/`](../product/README.md) và các bài test (`pytest tests/`).
