package com.example.aipa.controller;

import com.example.aipa.dto.user.UpdateProfileRequest;
import com.example.aipa.dto.user.UpdateProfileResponse;
import com.example.aipa.model.User;
import com.example.aipa.security.JwtService;
import com.example.aipa.service.UserService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/user")
@CrossOrigin(value = "*")
@RequiredArgsConstructor
public class UserController {
    private final UserService userService;
    private final JwtService jwtService;

    @PutMapping("/profile")
    public ResponseEntity<UpdateProfileResponse> updateProfile(
            @AuthenticationPrincipal UserDetails principal,
            @Valid @RequestBody UpdateProfileRequest request
    ) {
        if (principal == null) {
            throw new IllegalArgumentException("Unauthorized");
        }

        User updatedUser = userService.updateOwnProfile(principal.getUsername(), request);
        String role = updatedUser.getRole() == 1 ? "ROLE_ADMIN" : "ROLE_USER";
        UserDetails updatedPrincipal = new org.springframework.security.core.userdetails.User(
                updatedUser.getUsername(),
                updatedUser.getPassword(),
                java.util.List.of(new org.springframework.security.core.authority.SimpleGrantedAuthority(role))
        );

        String accessToken = jwtService.generateToken(updatedPrincipal, role);

        return ResponseEntity.ok(
                new UpdateProfileResponse(
                        updatedUser.getId(),
                        updatedUser.getUsername(),
                        updatedUser.getEmail(),
                        updatedUser.isActive(),
                        updatedUser.getRole(),
                        updatedUser.getRegistrationTimestamp(),
                        accessToken,
                        "Bearer",
                        "Profile updated successfully"
                )
        );
    }
}
