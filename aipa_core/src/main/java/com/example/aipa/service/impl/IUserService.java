package com.example.aipa.service.impl;

import com.example.aipa.dto.user.UpdateProfileRequest;
import com.example.aipa.model.User;

import java.util.List;
import java.util.Optional;

public interface IUserService {
    Optional<User> findByUsername(String username);

    Optional<User> findByEmail(String email);

    List<User> findAll();

    void deleteById(Long id);

    void deleteAll();

    Optional<User> findByFaceEmbeddingsJson(String faceEmbeddingsJson);

    Optional<User> updateUser(User user);

    User updateOwnProfile(String currentUsername, UpdateProfileRequest request);
}
