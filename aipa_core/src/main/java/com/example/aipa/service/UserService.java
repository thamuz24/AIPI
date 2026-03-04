package com.example.aipa.service;

import com.example.aipa.dto.user.AdminBanLogView;
import com.example.aipa.dto.user.UpdateProfileRequest;
import com.example.aipa.model.User;
import com.example.aipa.model.UserBanLog;
import com.example.aipa.repository.IUserRepository;
import com.example.aipa.repository.UserBanLogRepository;
import com.example.aipa.service.impl.IUserService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

@Service
public class UserService implements IUserService {
    @Autowired
    private IUserRepository userRepository;
    @Autowired
    private UserBanLogRepository userBanLogRepository;

    @Override
    public Optional<User> findByUsername(String username) {
        if (username == null || username.isBlank()) {
            return Optional.empty();
        }
        return userRepository.findByUsername(username);
    }

    @Override
    public Optional<User> findByEmail(String email) {
        if (email == null || email.isBlank()) {
            return Optional.empty();
        }
        return userRepository.findByEmail(email);
    }

    @Override
    public List<User> findAll() {
        return userRepository.findAll();
    }

    @Override
    public void deleteById(Long id) {
        userRepository.deleteById(id);
    }

    @Override
    public void deleteAll() {
        userRepository.deleteAll();
    }

    @Override
    public Optional<User> findByFaceEmbeddingsJson(String faceEmbeddingsJson) {
        if (faceEmbeddingsJson == null || faceEmbeddingsJson.isBlank()) {
            return Optional.empty();
        }
        return userRepository.findByFaceEmbeddingsJson(faceEmbeddingsJson);
    }

    @Override
    public Optional<User> updateUser(User user) {
        if (user == null || user.getId() == null) {
            return Optional.empty();
        }

        return userRepository.findById(user.getId())
                .map(existingUser -> userRepository.save(user));
    }

    @Override
    public User updateOwnProfile(String currentUsername, UpdateProfileRequest request) {
        if (currentUsername == null || currentUsername.isBlank()) {
            throw new IllegalArgumentException("Unauthorized");
        }

        User user = userRepository.findByUsername(currentUsername)
                .orElseThrow(() -> new IllegalArgumentException("User not found"));

        String username = request.getUsername().trim();
        String email = request.getEmail().trim().toLowerCase();

        userRepository.findByUsername(username)
                .filter(existing -> !existing.getId().equals(user.getId()))
                .ifPresent(existing -> {
                    throw new IllegalArgumentException("Username already exists");
                });

        userRepository.findByEmail(email)
                .filter(existing -> !existing.getId().equals(user.getId()))
                .ifPresent(existing -> {
                    throw new IllegalArgumentException("Email already exists");
                });

        user.setUsername(username);
        user.setEmail(email);
        return userRepository.save(user);
    }

    public Optional<User> registerUser(User user) {
        if (user == null) {
            return Optional.empty();
        }
        return Optional.of(userRepository.save(user));
    }

    public Optional<User> loginUser(String username, String password) {
        if (username == null || password == null) {
            return Optional.empty();
        }
        return userRepository.findByUsername(username)
                .filter(user -> user.getPassword().equals(password));
    }

    public List<User> getAllUsersForAdmin() {
        return userRepository.findAll();
    }

    public void banUser(Long userId, String adminUsername, String reason) {
        if (adminUsername == null || adminUsername.isBlank()) {
            throw new IllegalArgumentException("Unauthorized");
        }

        User user = userRepository.findById(userId)
                .orElseThrow(() -> new IllegalArgumentException("User not found"));

        if (user.getRole() == 1) {
            throw new IllegalArgumentException("Cannot ban admin account");
        }

        if (!user.isActive()) {
            throw new IllegalArgumentException("User is already banned");
        }

        user.setActive(false);
        userRepository.save(user);

        UserBanLog banLog = new UserBanLog();
        banLog.setUserId(user.getId());
        banLog.setUsername(user.getUsername());
        banLog.setEmail(user.getEmail());
        banLog.setReason(reason.trim());
        banLog.setBannedBy(adminUsername);
        userBanLogRepository.save(banLog);
    }

    public List<AdminBanLogView> getBanLogsForAdmin() {
        return userBanLogRepository.findAllByOrderByBannedAtDesc().stream()
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
