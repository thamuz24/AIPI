package com.example.aipa.dto.auth;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class RegisterRequest {
    @NotBlank(message = "username is required")
    @Size(min = 3, max = 50, message = "username length must be between 3 and 50")
    private String username;

    @NotBlank(message = "email is required")
    @Email(message = "email is invalid")
    private String email;

    @NotBlank(message = "password is required")
    @Size(min = 6, max = 72, message = "password length must be between 6 and 72")
    private String password;

    @NotBlank(message = "faceEmbeddingsJson is required")
    @Size(min = 10, max = 30000, message = "faceEmbeddingsJson length is invalid")
    private String faceEmbeddingsJson;
}
