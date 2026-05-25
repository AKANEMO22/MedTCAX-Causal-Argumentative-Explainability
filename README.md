# Causal Argumentation Framework — FCI Post-Processing Improvement

## Tổng quan

Trong phương pháp tiếp cận trước đây, cơ chế force_sink được sử dụng với mục đích chính là ngăn chặn các liên kết đầu ra từ biến kết quả (outcome) và loại bỏ các cạnh mơ hồ. Mặc dù cách tiếp cận này phần nào hạn chế được tình trạng suy luận ngược, nhưng thực tế vẫn tồn tại các liên kết phản trực quan; ví dụ, mô hình vẫn xuất hiện các kết nối không hợp lý như "tuổi tác là nguyên nhân gây suy thận" (đảo ngược mối quan hệ nhân quả thực tế).

Để khắc phục hạn chế này, giải pháp của chúng tôi đề xuất áp dụng cơ chế phân tầng (tier-based constraint) trong quá trình thực thi thuật toán FCI (Fast Causal Inference). Việc tích hợp ràng buộc thứ bậc giúp kiểm soát hướng của các liên kết dựa trên tri thức miền (domain knowledge), từ đó loại bỏ hoàn toàn hiện tượng suy luận ngược không mong muốn. Kết quả thực nghiệm cho thấy cấu trúc đồ thị nhân quả được định hướng rõ ràng, chính xác hơn và đạt hiệu suất cải thiện đáng kể so với phương pháp cũ.

---

## Cải tiến trong phiên bản mới

### 1. Xoá `force_sink`, thay bằng hai hàm mới

#### `_edge_endpoints(edge, node1, node2)`

Helper để đọc đúng kiểu endpoint của một cạnh trong FCI graph, xử lý cả trường hợp node1 hoặc node2 có thể đứng ở vị trí đầu hoặc cuối của cạnh:

#### `clean_ambiguous_outcome_edges(graph, outcome_name)`
Xuất hiện sau khi chạy hàm run_dual_and_merge_with_unified , xử lý sau khi chạy xong fci đến công đoạn
Thay thế `force_sink`. Logic hoạt động có chọn lọc:
- Cạnh đã rõ ràng (`nb → outcome`) → **bỏ qua, không đụng vào**
- Cạnh `o–>` hoặc `<–>` vào outcome → **giải quyết bằng cách chọn hướng rõ ràng nhất có thể** (`nb → outcome`), đây là lựa chọn bảo thủ và an toàn nhất trong bối cảnh outcome là biến mục tiêu
- Cạnh có endpoint khác (ví dụ cạnh nằm ngoài nhóm trên) → **bỏ qua**

