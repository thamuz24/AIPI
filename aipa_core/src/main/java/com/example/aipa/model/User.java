package com.example.aipa.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.Setter;
import lombok.ToString;

@Entity
@Getter
@Setter
@ToString
@Table(
        name = "aipa_users",
        indexes = {
                @Index(name = "idx_aipa_users_username", columnList = "username"),
                @Index(name = "idx_aipa_users_email", columnList = "email")
        }
)
public class User {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true, nullable = false, length = 50)
    private String username;

    @Column(unique = true, nullable = false, length = 100)
    private String email;

    @ToString.Exclude
    @Column(nullable = false, length = 60)
    private String password;

    @Column(columnDefinition = "TEXT")
    private String faceEmbeddingsJson;

    @Column(name = "registration_timestamp", nullable = false, updatable = false)
    private Long registrationTimestamp;

    @Column(name = "is_active", nullable = false)
    private boolean isActive = true;

    @Column(nullable = false)
    private int role = 0;

    @Column(name = "login_fail_count", nullable = false)
    private int numberOfLoginsFails = 0;

    @PrePersist
    public void prePersist() {
        if (registrationTimestamp == null) {
            registrationTimestamp = System.currentTimeMillis();
        }
    }
}
