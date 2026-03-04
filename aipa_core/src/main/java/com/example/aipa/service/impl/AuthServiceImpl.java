package com.example.aipa.service.impl;

import com.example.aipa.dto.auth.FaceLoginRequest;
import com.example.aipa.dto.auth.AuthResponse;
import com.example.aipa.dto.auth.LoginRequest;
import com.example.aipa.dto.auth.RegisterRequest;
import com.example.aipa.model.User;
import com.example.aipa.repository.IUserRepository;
import com.example.aipa.security.JwtService;
import com.example.aipa.service.AuthService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.jsonwebtoken.JwtException;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.List;

@Service
@RequiredArgsConstructor
public class AuthServiceImpl implements AuthService {
    private final IUserRepository userRepository;
    private final AuthenticationManager authenticationManager;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Value("${auth.face-login-threshold:0.82}")
    private double faceLoginThreshold;

    @Override
    public AuthResponse login(LoginRequest request) {
        String usernameOrEmail = request.getUsernameOrEmail().trim();

        authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(usernameOrEmail, request.getPassword())
        );

        User user = userRepository.findByUsernameOrEmail(usernameOrEmail)
                .orElseThrow(() -> new BadCredentialsException("Invalid username/email or password"));

        org.springframework.security.core.userdetails.User principal =
                buildPrincipal(user);
        String role = resolveRole(user);
        String accessToken = jwtService.generateToken(principal, role);
        String refreshToken = jwtService.generateRefreshToken(principal);
        return new AuthResponse(accessToken, "Bearer", role, refreshToken, "Login successful");
    }

    @Override
    public AuthResponse loginByFace(FaceLoginRequest request) {
        double[] loginVector = parseEmbeddingVector(request.getFaceEmbeddingsJson());

        List<User> candidates = userRepository.findByIsActiveTrueAndFaceEmbeddingsJsonIsNotNull();
        if (candidates.isEmpty()) {
            throw new BadCredentialsException("Chua co du lieu khuon mat de xac thuc");
        }

        User matchedUser = null;
        double bestScore = -1d;

        for (User candidate : candidates) {
            double[] candidateVector;
            try {
                candidateVector = parseEmbeddingVector(candidate.getFaceEmbeddingsJson());
            } catch (IllegalArgumentException ignored) {
                continue;
            }

            double score = cosineSimilarity(loginVector, candidateVector);
            if (score > bestScore) {
                bestScore = score;
                matchedUser = candidate;
            }
        }

        if (matchedUser == null || bestScore < faceLoginThreshold) {
            throw new BadCredentialsException("Xac thuc khuon mat that bai");
        }

        org.springframework.security.core.userdetails.User principal = buildPrincipal(matchedUser);
        String role = resolveRole(matchedUser);
        String accessToken = jwtService.generateToken(principal, role);
        String refreshToken = jwtService.generateRefreshToken(principal);
        return new AuthResponse(accessToken, "Bearer", role, refreshToken, "Dang nhap khuon mat thanh cong");
    }

    @Override
    public AuthResponse register(RegisterRequest request) {
        String username = request.getUsername().trim();
        String email = request.getEmail().trim().toLowerCase();
        String faceEmbeddingsJson = request.getFaceEmbeddingsJson().trim();

        if (userRepository.findByUsername(username).isPresent()) {
            throw new IllegalArgumentException("Username already exists");
        }
        if (userRepository.findByEmail(email).isPresent()) {
            throw new IllegalArgumentException("Email already exists");
        }
        parseEmbeddingVector(faceEmbeddingsJson);

        User user = new User();
        user.setUsername(username);
        user.setEmail(email);
        user.setPassword(passwordEncoder.encode(request.getPassword()));
        user.setFaceEmbeddingsJson(faceEmbeddingsJson);
        user.setRole(0);
        user.setActive(true);

        User savedUser = userRepository.save(user);
        org.springframework.security.core.userdetails.User principal =
                buildPrincipal(savedUser);
        String role = resolveRole(savedUser);
        String accessToken = jwtService.generateToken(principal, role);
        String refreshToken = jwtService.generateRefreshToken(principal);
        return new AuthResponse(accessToken, "Bearer", role, refreshToken, "Register successful");
    }

    @Override
    public AuthResponse refreshToken(String refreshToken) {
        String username;
        try {
            username = jwtService.extractUsername(refreshToken);
        } catch (JwtException | IllegalArgumentException ex) {
            throw new BadCredentialsException("Invalid refresh token");
        }

        User user = userRepository.findByUsernameOrEmail(username)
                .orElseThrow(() -> new BadCredentialsException("User not found"));

        UserDetails principal = buildPrincipal(user);
        try {
            if (!jwtService.isRefreshTokenValid(refreshToken, principal)) {
                throw new BadCredentialsException("Invalid refresh token");
            }
        } catch (JwtException | IllegalArgumentException ex) {
            throw new BadCredentialsException("Refresh token expired or invalid");
        }

        String role = resolveRole(user);
        String newAccessToken = jwtService.generateToken(principal, role);
        String newRefreshToken = jwtService.generateRefreshToken(principal);
        return new AuthResponse(newAccessToken, "Bearer", role, newRefreshToken, "Token refreshed");
    }

    private double[] parseEmbeddingVector(String faceEmbeddingsJson) {
        if (faceEmbeddingsJson == null || faceEmbeddingsJson.isBlank()) {
            throw new IllegalArgumentException("Face embedding data is required");
        }

        JsonNode rootNode;
        try {
            rootNode = objectMapper.readTree(faceEmbeddingsJson);
        } catch (IOException ex) {
            throw new IllegalArgumentException("Face embedding data is invalid", ex);
        }

        JsonNode vectorNode = rootNode;
        if (rootNode != null && rootNode.isObject()) {
            if (rootNode.has("vector")) {
                vectorNode = rootNode.get("vector");
            } else if (rootNode.has("embedding")) {
                vectorNode = rootNode.get("embedding");
            }
        }

        if (vectorNode == null || !vectorNode.isArray() || vectorNode.isEmpty()) {
            throw new IllegalArgumentException("Face embedding vector is invalid");
        }

        double[] vector = new double[vectorNode.size()];
        for (int i = 0; i < vectorNode.size(); i++) {
            JsonNode node = vectorNode.get(i);
            if (node == null || !node.isNumber()) {
                throw new IllegalArgumentException("Face embedding vector is invalid");
            }
            vector[i] = node.asDouble();
        }
        return vector;
    }

    private double cosineSimilarity(double[] first, double[] second) {
        if (first == null || second == null || first.length == 0 || second.length == 0 || first.length != second.length) {
            return -1d;
        }

        double dot = 0d;
        double normFirst = 0d;
        double normSecond = 0d;
        for (int i = 0; i < first.length; i++) {
            dot += first[i] * second[i];
            normFirst += first[i] * first[i];
            normSecond += second[i] * second[i];
        }

        if (normFirst <= 0d || normSecond <= 0d) {
            return -1d;
        }
        return dot / (Math.sqrt(normFirst) * Math.sqrt(normSecond));
    }

    private String resolveRole(User user) {
        return user.getRole() == 1 ? "ROLE_ADMIN" : "ROLE_USER";
    }

    private org.springframework.security.core.userdetails.User buildPrincipal(User user) {
        String role = resolveRole(user);
        return new org.springframework.security.core.userdetails.User(
                user.getUsername(),
                user.getPassword(),
                user.isActive(),
                true,
                true,
                true,
                List.of(
                        new org.springframework.security.core.authority.SimpleGrantedAuthority(role)
                )
        );
    }
}
