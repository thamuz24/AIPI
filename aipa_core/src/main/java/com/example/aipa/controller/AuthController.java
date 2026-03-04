package com.example.aipa.controller;

import com.example.aipa.dto.auth.LoginRequest;
import com.example.aipa.dto.auth.FaceLoginRequest;
import com.example.aipa.dto.auth.RefreshTokenRequest;
import com.example.aipa.dto.auth.RegisterRequest;
import com.example.aipa.service.AuthService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/login")
    public ResponseEntity<?> login(@Valid @RequestBody LoginRequest request) {
        return ResponseEntity.ok(authService.login(request));
    }

    @PostMapping("/login-face")
    public ResponseEntity<?> loginByFace(@Valid @RequestBody FaceLoginRequest request) {
        return ResponseEntity.ok(authService.loginByFace(request));
    }

    @PostMapping("/register")
    public ResponseEntity<?> register(@Valid @RequestBody RegisterRequest request) {
        return ResponseEntity.ok(authService.register(request));
    }

    @PostMapping("/refresh")
    public ResponseEntity<?> refresh(@Valid @RequestBody RefreshTokenRequest request) {
        return ResponseEntity.ok(authService.refreshToken(request.getRefreshToken()));
    }
}
