package com.example.aipa.dto.auth;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class LoginRequest {
    @NotBlank(message = "usernameOrEmail is required")
    private String usernameOrEmail;

    @NotBlank(message = "password is required")
    private String password;
}
