package com.example.aipa.dto.user;

import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class AdminUserView {
    private Long id;
    private String username;
    private String email;
    private boolean active;
    private int role;
    private Long registrationTimestamp;
}
