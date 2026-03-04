package com.example.aipa.controller;

import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/api")
public class SecurityTestController {
    @GetMapping("/user/ping")
    public Map<String, String> userPing() {
        return Map.of("message", "User access granted");
    }

    @GetMapping("/user/me")
    public Map<String, Object> me(Authentication authentication) {
        return Map.of(
                "username", authentication.getName(),
                "authorities", authentication.getAuthorities()
        );
    }

    @GetMapping("/admin/ping")
    public Map<String, String> adminPing() {
        return Map.of("message", "Admin access granted");
    }
}
