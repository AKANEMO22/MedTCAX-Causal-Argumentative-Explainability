# Causal Argumentation Framework — FCI Post-Processing Improvement

## Tổng quan

Trong phương pháp tiếp cận trước đây, cơ chế force_sink được sử dụng với mục đích chính là ngăn chặn các liên kết đầu ra từ biến kết quả (outcome) và loại bỏ các cạnh mơ hồ. Mặc dù cách tiếp cận này phần nào hạn chế được tình trạng suy luận ngược, nhưng thực tế vẫn tồn tại các liên kết phản trực quan; ví dụ, mô hình vẫn xuất hiện các kết nối không hợp lý như "tuổi tác là nguyên nhân gây suy thận" (đảo ngược mối quan hệ nhân quả thực tế).

Để khắc phục hạn chế này, giải pháp của chúng tôi đề xuất áp dụng cơ chế phân tầng (tier-based constraint) trong quá trình thực thi thuật toán FCI (Fast Causal Inference). Việc tích hợp ràng buộc thứ bậc giúp kiểm soát hướng của các liên kết dựa trên tri thức miền (domain knowledge), từ đó loại bỏ hoàn toàn hiện tượng suy luận ngược không mong muốn. Kết quả thực nghiệm cho thấy cấu trúc đồ thị nhân quả được định hướng rõ ràng, chính xác hơn và đạt hiệu suất cải thiện đáng kể so với phương pháp cũ.

---

## Cải tiến trong phiên bản mới
Phiên bản causal_arg_with_tier bổ sung cơ chế Tier-based Background Knowledge, cho phép người dùng mã hóa tri thức miền (domain knowledge) về thứ tự nhân quả của các nhóm feature trực tiếp vào quá trình khám phá nhân quả FCI/PC. Thay vì để thuật toán tự do định hướng tất cả các cạnh, phiên bản mới ràng buộc các cạnh phải đi từ tier thấp hơn đến tier cao hơn, loại bỏ những định hướng phi lý về mặt ngữ nghĩa.

Các hàm mới được thêm vào
Nhóm 1 — Xây dựng Tier (chạy trước FCI/PC)

define_tiers(tier_groups)

Vị trí trong pipeline: Trước khi gọi run_dual_and_merge_with_unified(), ở bước khai báo cấu hình.
Nhận vào một dictionary dạng {tier_index: [danh_sách_feature]} do người dùng định nghĩa và chuyển đổi thành một dictionary ngược chiều {feature: tier_index} để tra cứu nhanh. Hàm này đảm bảo không có feature nào được gán vào nhiều tier cùng lúc và ném lỗi rõ ràng nếu phát hiện xung đột. Đây là điểm vào duy nhất để người dùng khai báo giả thiết nhân quả về thứ tự thời gian hoặc cấu trúc domain.

ensure_all_tiered(feature_tiers, features, outcome)

Vị trí trong pipeline: Ngay trong _run_discovery(), trước khi mã hóa dữ liệu và chạy FCI/PC.
Kiểm tra rằng mọi feature trong danh sách và biến outcome đều đã được gán tier. Nếu bất kỳ biến nào bị bỏ sót, hàm ném ValueError với danh sách cụ thể các biến thiếu. Vai trò của hàm là "gate keeper" — ngăn chặn việc chạy FCI với bảng tier không đầy đủ, tránh hành vi không xác định khi xây BackgroundKnowledge.

map_dummy_tiers(encoding_groups, feature_tiers, col_names)

Vị trí trong pipeline: Trong _run_discovery(), sau khi mã hóa dữ liệu (_prepare_discovery_encoding), trước khi xây BackgroundKnowledge.
Sau bước one-hot encoding, các cột gốc như pclass bị thay thế bởi pclass_1, pclass_2, pclass_3. Hàm này lan truyền tier từ feature gốc sang tất cả các cột encoded tương ứng dựa trên encoding_groups. Nếu không có bước này, BackgroundKnowledge sẽ không biết pclass_1 thuộc tier nào và sẽ không ràng buộc được hướng cạnh đúng cách.


build_background_knowledge(col_names, col_tiers)

Vị trí trong pipeline: Trong _run_discovery(), sau map_dummy_tiers(), ngay trước lời gọi fci() hoặc pc().
Xây dựng đối tượng BackgroundKnowledge của thư viện causal-learn từ bảng tier đã được ánh xạ đến cột encoded. Với mỗi cặp cột (A, B), nếu tier của A cao hơn tier của B (tức A không thể là nguyên nhân của B theo giả thiết domain), hàm thêm ràng buộc forbidden vào BackgroundKnowledge. Kết quả là FCI/PC sẽ không bao giờ đề xuất cạnh đi từ nhóm đặc trưng bậc cao hơn (ví dụ: fare) về nhóm bậc thấp hơn (ví dụ: age, sex). Hàm phải tạo đối tượng GraphNode thay vì truyền chuỗi trực tiếp vì đây là yêu cầu của API causal-learn.

Nhóm 2 — Xử lý đồ thị sau FCI (chạy sau FCI)


_edge_has_circle(edge, node_a, node_b)

Vị trí trong pipeline: Được gọi nội bộ bởi remove_ambiguous_same_tier_edges(), ngay sau lời gọi fci().
Hàm helper kiểm tra xem một cạnh trong đồ thị FCI có chứa endpoint kiểu CIRCLE (o) hay không. Trong ký hiệu PAG của FCI, o-> hoặc o-o biểu thị sự không chắc chắn về hướng hoặc sự tồn tại của confounders ẩn. Việc phát hiện loại endpoint này là điều kiện tiên quyết để quyết định có nên xóa cạnh không.

remove_ambiguous_same_tier_edges(graph, col_tiers)

Vị trí trong pipeline: Trong _run_discovery(), ngay sau lời gọi fci()
Duyệt qua tất cả các cặp node trong cùng một tier và xóa bất kỳ cạnh nào có endpoint dạng CIRCLE. Lý do: khi hai biến thuộc cùng tier (ví dụ age và sex đều ở tier 1 — đặc trưng bẩm sinh), bất kỳ định hướng nào giữa chúng mà FCI không thể xác định chắc chắn (biểu thị bằng o) đều không có ý nghĩa nhân quả và nên bị loại bỏ thay vì giữ lại như một cạnh mơ hồ. Cơ chế này thay thế force_sink() trước đây vốn áp đặt cứng nhắc hướng về phía outcome mà không xem xét tính nhất quán tier.
