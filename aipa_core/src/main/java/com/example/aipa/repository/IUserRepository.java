package com.example.aipa.repository;

import com.example.aipa.model.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.List;

@Repository
public interface IUserRepository extends JpaRepository<User, Long> {
    Optional<User> findByUsername(String username);

    Optional<User> findByEmail(String email);

    Optional<User> findByFaceEmbeddingsJson(String faceEmbeddingsJson);

    List<User> findByIsActiveTrueAndFaceEmbeddingsJsonIsNotNull();

    @Query("SELECT u FROM User u WHERE u.username = :usernameOrEmail OR u.email = :usernameOrEmail")
    Optional<User> findByUsernameOrEmail(String usernameOrEmail);
}
