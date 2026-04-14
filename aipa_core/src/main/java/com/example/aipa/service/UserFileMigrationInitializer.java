package com.example.aipa.service;

import com.example.aipa.model.User;
import com.example.aipa.model.UserBanLog;
import com.example.aipa.repository.IUserRepository;
import com.example.aipa.repository.UserBanLogRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
@ConditionalOnProperty(name = "aipa.user-store.migrate-from-db", havingValue = "true")
@RequiredArgsConstructor
public class UserFileMigrationInitializer {
    private final UserFileStoreService userFileStoreService;
    private final IUserRepository userRepository;
    private final UserBanLogRepository userBanLogRepository;

    @EventListener(ApplicationReadyEvent.class)
    public void migrateExistingDatabaseUsers() {
        List<User> users = userRepository.findAll();
        List<UserBanLog> banLogs = userBanLogRepository.findAll();
        userFileStoreService.seedStoreIfEmpty(users, banLogs);
    }
}
