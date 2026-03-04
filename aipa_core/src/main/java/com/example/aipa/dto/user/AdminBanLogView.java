package com.example.aipa.dto.user;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class AdminBanLogView {
    private Long id;
    private Long userId;
    private String username;
    private String email;
    private String reason;
    private String bannedBy;
    private Long bannedAt;
}
