package com.example.aipa.repository;

import com.example.aipa.model.UserBanLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface UserBanLogRepository extends JpaRepository<UserBanLog, Long> {
    List<UserBanLog> findAllByOrderByBannedAtDesc();
}
