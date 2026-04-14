package com.example.aipa.service;

import com.example.aipa.dto.user.AdminBanLogView;
import com.example.aipa.dto.user.UpdateProfileRequest;
import com.example.aipa.model.User;
import com.example.aipa.model.UserBanLog;
import com.example.aipa.service.impl.IUserService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class UserService implements IUserService {
    private final UserFileStoreService userFileStoreService;

    @Override
    public Optional<User> findByUsername(String username) {
        if (username == null || username.isBlank()) {
            return Optional.empty();
        }
        return userFileStoreService.findByUsername(username);
    }

    @Override
    public Optional<User> findByEmail(String email) {
        if (email == null || email.isBlank()) {
            return Optional.empty();
        }
        return userFileStoreService.findByEmail(email);
    }

    @Override
    public List<User> findAll() {
        return userFileStoreService.findAllUsers();
    }

    @Override
    public void deleteById(Long id) {
        userFileStoreService.deleteUserById(id);
    }

    @Override
    public void deleteAll() {
        userFileStoreService.deleteAllUsers();
    }

    @Override
    public Optional<User> findByFaceEmbeddingsJson(String faceEmbeddingsJson) {
        if (faceEmbeddingsJson == null || faceEmbeddingsJson.isBlank()) {
            return Optional.empty();
        }
        return userFileStoreService.findByFaceEmbeddingsJson(faceEmbeddingsJson);
    }

    @Override
    public Optional<User> updateUser(User user) {
        if (user == null || user.getId() == null) {
            return Optional.empty();
        }

        return userFileStoreService.findUserById(user.getId())
                .map(existingUser -> userFileStoreService.saveUser(user));
    }

    @Override
    public User updateOwnProfile(String currentUsername, UpdateProfileRequest request) {
        if (currentUsername == null || currentUsername.isBlank()) {
            throw new IllegalArgumentException("Unauthorized");
        }

        User user = userFileStoreService.findByUsername(currentUsername)
                .orElseThrow(() -> new IllegalArgumentException("User not found"));

        String username = request.getUsername().trim();
        String email = request.getEmail().trim().toLowerCase();

        userFileStoreService.findByUsername(username)
                .filter(existing -> !existing.getId().equals(user.getId()))
                .ifPresent(existing -> {
                    throw new IllegalArgumentException("Username already exists");
                });

        userFileStoreService.findByEmail(email)
                .filter(existing -> !existing.getId().equals(user.getId()))
                .ifPresent(existing -> {
                    throw new IllegalArgumentException("Email already exists");
                });

        user.setUsername(username);
        user.setEmail(email);
        return userFileStoreService.saveUser(user);
    }

    public Optional<User> registerUser(User user) {
        if (user == null) {
            return Optional.empty();
        }
        return Optional.of(userFileStoreService.saveUser(user));
    }

    public Optional<User> loginUser(String username, String password) {
        if (username == null || password == null) {
            return Optional.empty();
        }
        return userFileStoreService.findByUsername(username)
                .filter(user -> user.getPassword().equals(password));
    }

    public List<User> getAllUsersForAdmin() {
        return userFileStoreService.findAllUsers();
    }

    public Optional<User> findByUsernameOrEmail(String usernameOrEmail) {
        return userFileStoreService.findByUsernameOrEmail(usernameOrEmail);
    }

    public List<User> getActiveUsersWithFaceEmbeddings() {
        return userFileStoreService.findActiveUsersWithFaceEmbeddings();
    }

    public void banUser(Long userId, String adminUsername, String reason) {
        if (adminUsername == null || adminUsername.isBlank()) {
            throw new IllegalArgumentException("Unauthorized");
        }

        User user = userFileStoreService.findUserById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found"));

        if (user.getRole() == 1) {
            throw new IllegalArgumentException("Cannot ban admin account");
        }

        if (!user.isActive()) {
            throw new IllegalArgumentException("User is already banned");
        }

        user.setActive(false);
        userFileStoreService.saveUser(user);

        UserBanLog banLog = new UserBanLog();
        banLog.setUserId(user.getId());
        banLog.setUsername(user.getUsername());
        banLog.setEmail(user.getEmail());
        banLog.setReason(reason.trim());
        banLog.setBannedBy(adminUsername);
        userFileStoreService.saveBanLog(banLog);
    }

    public List<AdminBanLogView> getBanLogsForAdmin() {
        return userFileStoreService.findAllBanLogs().stream()
                .map(log -> new AdminBanLogView(
                        log.getId(),
                        log.getUserId(),
                        log.getUsername(),
                        log.getEmail(),
                        log.getReason(),
                        log.getBannedBy(),
                        log.getBannedAt()
                ))
                .toList();
    }
}
