package com.example.aipa.controller;

import com.example.aipa.dto.user.UserProfileView;
import com.example.aipa.model.User;
import com.example.aipa.service.UserService;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api")
public class SecurityTestController {
    private final UserService userService;

    public SecurityTestController(UserService userService) {
        this.userService = userService;
    }

    @GetMapping("/user/ping")
    public Map<String, String> userPing() {
        return Map.of("message", "User access granted");
    }

    @GetMapping("/user/me")
    public UserProfileView me(Authentication authentication) {
        if (authentication == null || authentication.getName() == null || authentication.getName().isBlank()) {
            throw new IllegalArgumentException("Unauthorized");
        }

        User user = userService.findByUsername(authentication.getName())
                .orElseThrow(() -> new IllegalArgumentException("User not found"));

        return new UserProfileView(
                user.getId(),
                user.getUsername(),
                user.getEmail(),
                user.isActive(),
                user.getRole(),
                user.getRegistrationTimestamp()
        );
    }

    @GetMapping("/admin/ping")
    public Map<String, String> adminPing() {
        return Map.of("message", "Admin access granted");
    }
}
