package com.example.aipa.controller;

import com.example.aipa.dto.user.AdminBanLogView;
import com.example.aipa.dto.user.BanUserRequest;
import com.example.aipa.dto.user.AdminUserView;
import com.example.aipa.model.User;
import com.example.aipa.service.UserService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/admin/users")
@RequiredArgsConstructor
public class AdminUserController {
    private final UserService userService;

    @GetMapping
    public ResponseEntity<List<AdminUserView>> getRegisteredUsers() {
        List<AdminUserView> users = userService.getAllUsersForAdmin().stream()
                .map(this::toView)
                .toList();
        return ResponseEntity.ok(users);
    }

    @GetMapping("/ban-logs")
    public ResponseEntity<List<AdminBanLogView>> getBanLogs() {
        return ResponseEntity.ok(userService.getBanLogsForAdmin());
    }

    @PatchMapping("/{id}/ban")
    public ResponseEntity<Map<String, String>> banUser(
            @PathVariable Long id,
            @AuthenticationPrincipal UserDetails principal,
            @Valid @RequestBody BanUserRequest request
    ) {
        if (principal == null) {
            throw new IllegalArgumentException("Unauthorized");
        }

        userService.banUser(id, principal.getUsername(), request.getReason());
        return ResponseEntity.ok(Map.of("message", "User has been banned"));
    }

    private AdminUserView toView(User user) {
        return new AdminUserView(
                user.getId(),
                user.getUsername(),
                user.getEmail(),
                user.isActive(),
                user.getRole(),
                user.getRegistrationTimestamp()
        );
    }
}
