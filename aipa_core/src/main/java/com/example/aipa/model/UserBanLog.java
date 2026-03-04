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
        name = "aipa_user_ban_logs",
        indexes = {
                @Index(name = "idx_ban_logs_user_id", columnList = "user_id"),
                @Index(name = "idx_ban_logs_banned_at", columnList = "banned_at")
        }
)
public class UserBanLog {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(nullable = false, length = 50)
    private String username;

    @Column(nullable = false, length = 100)
    private String email;

    @Column(nullable = false, length = 255)
    private String reason;

    @Column(name = "banned_by", nullable = false, length = 50)
    private String bannedBy;

    @Column(name = "banned_at", nullable = false, updatable = false)
    private Long bannedAt;

    @PrePersist
    public void prePersist() {
        if (bannedAt == null) {
            bannedAt = System.currentTimeMillis();
        }
    }
}
