package com.example.aipa.dto;
import lombok.Data;

//** Lớp DTO để đăng nhập user bằng mật khẩu */
//** Chứa các trường cần thiết để xác thực user */
//** Sử dụng trong quá trình đăng nhập tài khoản bằng mật khẩu */
@Data
public class UserLoginByPassword {
    // Trường có thể là username hoặc email
    private String usernameOrEmail;
    // Mật khẩu
    private String password;
}
