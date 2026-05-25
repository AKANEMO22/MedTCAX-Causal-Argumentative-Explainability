# Causal Argumentation Framework — FCI Post-Processing Improvement

## Tổng quan

Tài liệu này mô tả cải tiến được thực hiện trong file `causal_arg_with_tier.ipynb` so với phiên bản gốc `causal_arg_goc.ipynb`. Toàn bộ pipeline 7 bước (Dual Discovery → Merge → Unified Graph → BAF → AF → Extensions → Acceptance) **không thay đổi**. Chỉ có một thay đổi tập trung duy nhất: **cách xử lý graph sau khi FCI chạy xong**.

---

## Vấn đề với phiên bản gốc

### Hàm `force_sink` — cưỡng bức không phân biệt

Phiên bản gốc sử dụng hàm `force_sink` để đảm bảo outcome node luôn là "sink" (chỉ nhận cạnh vào, không có cạnh ra):

```python
# File gốc — trong _run_discovery()
graph = _unwrap_graph(res)
force_sink(graph, outcome)   # ← gọi cho CẢ PC lẫn FCI
```

Hàm này hoạt động bằng cách xoá toàn bộ cạnh liền kề outcome rồi **ép lại thành `nb → outcome`**, bất kể cạnh đó đang mang loại endpoint nào từ FCI trả về.

**Hệ quả:** FCI là thuật toán đặc biệt — nó phân biệt ba loại endpoint khác nhau, mỗi loại mang ý nghĩa về cấu trúc causal:

| Ký hiệu FCI | Endpoint type | Ý nghĩa |
|---|---|---|
| `–>` | TAIL → ARROW | Cạnh có hướng rõ ràng |
| `o–>` | CIRCLE → ARROW | Hướng chưa chắc chắn (có thể có latent confounder) |
| `<–>` | ARROW ↔ ARROW | Bidirected — chắc chắn có latent confounder |

Khi `force_sink` chạy, nó xoá và ghi đè **tất cả** các loại trên thành `TAIL → ARROW` mà không phân biệt. Kết quả là thông tin quý giá mà FCI đã suy luận về latent confounders bị **mất hoàn toàn** trước khi đưa vào BAF.

---

## Cải tiến trong phiên bản mới

### 1. Xoá `force_sink`, thay bằng hai hàm mới

#### `_edge_endpoints(edge, node1, node2)`

Helper để đọc đúng kiểu endpoint của một cạnh trong FCI graph, xử lý cả trường hợp node1/node2 có thể đứng ở vị trí đầu hoặc cuối của cạnh:

```python
def _edge_endpoints(edge, node1, node2):
    if hasattr(edge, "get_endpoint"):
        return edge.get_endpoint(node1), edge.get_endpoint(node2)
    n1 = edge.get_node1()
    if n1 == node1:
        return edge.get_endpoint1(), edge.get_endpoint2()
    return edge.get_endpoint2(), edge.get_endpoint1()
```

#### `clean_ambiguous_outcome_edges(graph, outcome_name)`

Thay thế `force_sink`. Logic hoạt động có chọn lọc:

```python
def clean_ambiguous_outcome_edges(graph, outcome_name: str):
    outcome = graph.get_node(outcome_name)
    neighbors = list(graph.get_adjacent_nodes(outcome))
    for nb in neighbors:
        edge = graph.get_edge(outcome, nb)
        ep_out, ep_nb = _edge_endpoints(edge, outcome, nb)

        # ✅ Giữ nguyên nếu cạnh đã đúng hướng: nb → outcome
        if ep_nb == Endpoint.TAIL and ep_out == Endpoint.ARROW:
            continue

        # 🔧 Chỉ sửa nếu cạnh mơ hồ: circle hoặc bidirected
        is_circle = ep_out == Endpoint.CIRCLE or ep_nb == Endpoint.CIRCLE
        is_bidirected = ep_out == Endpoint.ARROW and ep_nb == Endpoint.ARROW
        if not (is_circle or is_bidirected):
            continue

        # Xoá cạnh mơ hồ, thay bằng hướng rõ ràng nb → outcome
        graph.remove_edge(edge)
        graph.add_directed_edge(nb, outcome)
```

**Điểm mấu chốt của logic này:**

- Cạnh đã rõ ràng (`nb → outcome`) → **bỏ qua, không đụng vào**
- Cạnh `o–>` hoặc `<–>` vào outcome → **giải quyết bằng cách chọn hướng rõ ràng nhất có thể** (`nb → outcome`), đây là lựa chọn bảo thủ và an toàn nhất trong bối cảnh outcome là biến mục tiêu
- Cạnh có endpoint khác (ví dụ cạnh nằm ngoài nhóm trên) → **bỏ qua**

### 2. Thay đổi trong `_run_discovery` — chỉ áp dụng cho FCI

```python
# Phiên bản gốc
graph = _unwrap_graph(res)
force_sink(graph, outcome)          # áp dụng cho cả PC và FCI

# Phiên bản mới
algo_l = algo.lower()
graph = _unwrap_graph(res)
if algo_l == "fci":
    clean_ambiguous_outcome_edges(graph, outcome)   # CHỈ cho FCI
```

Với PC, không cần xử lý thêm vì PC đã trả về DAG thuần (chỉ có TAIL và ARROW), không có endpoint mơ hồ. Áp dụng `force_sink` cho PC như file gốc là thừa và có nguy cơ làm mất cạnh đúng.

---

## So sánh hành vi

| Tình huống | File gốc (`force_sink`) | File mới (`clean_ambiguous`) |
|---|---|---|
| Cạnh `nb → outcome` đã đúng | Xoá rồi tạo lại (vô nghĩa, rủi ro lỗi) | Giữ nguyên |
| Cạnh `o–> outcome` (circle) | Ép thành `nb → outcome` | Ép thành `nb → outcome` |
| Cạnh `<–> outcome` (bidirected) | Ép thành `nb → outcome` | Ép thành `nb → outcome` |
| Cạnh khác loại | Xoá và ghi đè toàn bộ | Bỏ qua |
| Áp dụng cho PC | Có (không cần thiết) | Không |
| Áp dụng cho FCI | Có | Có |

---

## Những gì **không thay đổi**

Tất cả các thành phần khác của pipeline giữ nguyên hoàn toàn:

- Entropy binning và encoding data (`_prepare_discovery_encoding`, `_prepare_unified_encoding`)
- Dual-run và merge orientation (`run_dual_and_merge_with_unified`, `merge_orientations`)
- Xây dựng unified encoded graph (`_ResultShim`, `_SimpleGraph`)
- Export graph có correlation (`export_causallearn_graph_with_corr`, `export_unified_graph_with_corr`, `export_group_graph_with_corr`)
- Toàn bộ lớp `BAF` và `AF` (supports, attacks, constellations, extensions, acceptance)
- Hàm `make_binary_sink`
- Cả 3 experiment: Titanic, Diabetes, COMPAS — cấu hình, tham số, output path đều giữ nguyên

---

## Lý do cải tiến này quan trọng

FCI (Fast Causal Inference) được thiết kế để hoạt động với dữ liệu có thể có **latent confounders** — các biến ẩn không được đo lường. Thông tin về sự tồn tại của latent confounders được mã hoá trong chính các loại endpoint (`o`, `↔`). Nếu ép tất cả về `→` ngay sau khi FCI chạy, pipeline đang **vứt bỏ phần thông tin đặc trưng nhất của FCI** so với PC trước khi bất kỳ bước nào khác có cơ hội sử dụng nó.

Cải tiến này giúp phần output của FCI được đưa vào BAF một cách **trung thực hơn với những gì thuật toán thực sự suy luận được**.

---

## Vị trí thay đổi trong code

| File | Vị trí | Nội dung |
|---|---|---|
| `causal_arg_goc.ipynb` | Cell "Helper methods" | Định nghĩa `force_sink` |
| `causal_arg_goc.ipynb` | Cell "Step 1.2" — hàm `_run_discovery` | Gọi `force_sink(graph, outcome)` vô điều kiện |
| `causal_arg_with_tier.ipynb` | Cell "Helper methods" | `force_sink` bị comment out; thêm `_edge_endpoints` và `clean_ambiguous_outcome_edges` |
| `causal_arg_with_tier.ipynb` | Cell "Step 1.2" — hàm `_run_discovery` | Thêm `algo_l = algo.lower()`; gọi `clean_ambiguous_outcome_edges` có điều kiện `if algo_l == "fci"` |
