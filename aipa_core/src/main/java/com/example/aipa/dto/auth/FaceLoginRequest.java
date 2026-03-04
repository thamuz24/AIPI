package com.example.aipa.dto.auth;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

@Data
public class FaceLoginRequest {
    @NotBlank(message = "faceEmbeddingsJson is required")
    @Size(min = 10, max = 30000, message = "faceEmbeddingsJson length is invalid")
    private String faceEmbeddingsJson;
}
