package com.example.aipa.dto;

import lombok.Data;

//** Lớp DTO để đăng nhập user bằng vector đặc trưng khuôn mặt */
//** Chứa các trường cần thiết để xác thực user */
//** Sử dụng trong quá trình đăng nhập tài khoản bằng nhận diện khuôn mặt */
@Data
public class UserLoginByFaceEmbedding {
    private String faceEmbeddingsJson;
}
