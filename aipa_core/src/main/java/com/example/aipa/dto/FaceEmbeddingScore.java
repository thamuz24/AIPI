package com.example.aipa.dto;

import lombok.Data;

//** Lớp DTO để biểu diễn điểm số so sánh vector đặc trưng khuôn mặt */
//** Chứa các trường cần thiết để lưu trữ điểm số so sánh */
//** Sử dụng trong quá trình xác thực khuôn mặt */
@Data
public class FaceEmbeddingScore {
    private String faceEmbeddingsJson;
    // Điểm số so sánh
    private double score;
    private Long userId;
    // Trạng thái so sánh (true nếu khớp, false nếu không khớp)
    private boolean status;
}
