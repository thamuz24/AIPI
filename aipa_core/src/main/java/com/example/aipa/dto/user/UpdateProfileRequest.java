package com.example.aipa.dto.user;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class UpdateProfileRequest {
    @NotBlank(message = "username is required")
    @Size(min = 3, max = 50, message = "username length must be between 3 and 50")
    private String username;

    @NotBlank(message = "email is required")
    @Email(message = "email is invalid")
    private String email;
}
