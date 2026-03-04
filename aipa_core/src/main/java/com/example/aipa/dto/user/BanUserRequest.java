package com.example.aipa.dto.user;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class BanUserRequest {
    @NotBlank(message = "reason is required")
    @Size(min = 5, max = 255, message = "reason length must be between 5 and 255")
    private String reason;
}
