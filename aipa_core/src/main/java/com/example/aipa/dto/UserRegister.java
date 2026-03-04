package com.example.aipa.dto;

import lombok.Data;

//** Lớp DTO để đăng ký user mới */
//** Chứa các trường cần thiết để tạo mới user */
//** Sử dụng trong quá trình đăng ký tài khoản mới */
@Data
public class UserRegister {

    private String username;
    private String email;
    private String password;
    private String faceEmbeddingsJson;

}
