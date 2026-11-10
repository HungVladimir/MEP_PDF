1. SUMITTER_EMAIL sẽ lấy ở cột thanh toán trong sheet "Thanh toán" ở file excel2, ta lấy giá trị và tự điền thêm @gmail.com, những giá trị nào đã có @yahoo.com.vn thì giữ nguyên. hiện tại chỉ có 2 loại @gmail.com hoặc @yahoo.com.vn thôi
Ví dụ nguyenthikimngan269 -> nguyenthikimngan269@gmail.com , themeteor_xt@yahoo.com.vn ( giữ nguyên)
2. Cơ sở dữ liệu đích, hiện tại sẽ test trên mbldb trước, y như code cũ của tôi, minio cũng giống, chỉ khác đường dẫn thay vì là mep_payment thì là aibill (aibill/2026-11/26a2dba1a5.png)
3. Tháng thanh toán cụ thể thì có thể lấy từ tên file excel được không, Các file sẽ có tên kiểu: (AI Crew) thanh toán hóa đơn tháng 2026.10.xlsx , (AI Crew) thanh toán hóa đơn tháng 2026.09.xlsx, (AI Crew) thanh toán hóa đơn tháng 2026.08.xlsx, từ file name đó có thể lấy được tháng thanh toán không?

Và ví dụ trong file excel 1 , 1 người mà mua cả gpt và claude thì sẽ lưu thành 2 dòng trong db, check xem còn điều gì chưa rõ thì hỏi để tôi trả lời, nếu ổn rồi thì bảo tôi