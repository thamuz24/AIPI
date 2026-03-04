package com.example.aipa.dto.user;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class UpdateProfileResponse {
    private Long id;
    private String username;
    private String email;
    private boolean active;
    private int role;
    private Long registrationTimestamp;
    private String accessToken;
    private String tokenType;
    private String message;
}
