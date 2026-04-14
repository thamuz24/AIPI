package com.example.aipa.service;

import com.example.aipa.model.User;
import com.example.aipa.model.UserBanLog;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;

@Service
public class UserFileStoreService {
    private final ObjectMapper objectMapper;
    private final Object monitor = new Object();
    private final Path storePath;

    public UserFileStoreService(@Value("${aipa.user-store.path:}") String configuredPath) {
        this.objectMapper = new ObjectMapper().enable(SerializationFeature.INDENT_OUTPUT);
        this.storePath = resolveStorePath(configuredPath);
        ensureStoreExists();
    }

    public List<User> findAllUsers() {
        synchronized (monitor) {
            return new ArrayList<>(readStore().users);
        }
    }

    public Optional<User> findUserById(Long id) {
        if (id == null) {
            return Optional.empty();
        }

        synchronized (monitor) {
            return readStore().users.stream()
                    .filter(user -> id.equals(user.getId()))
                    .findFirst();
        }
    }

    public Optional<User> findByUsername(String username) {
        if (username == null || username.isBlank()) {
            return Optional.empty();
        }

        String normalized = username.trim();
        synchronized (monitor) {
            return readStore().users.stream()
                    .filter(user -> normalized.equalsIgnoreCase(user.getUsername()))
                    .findFirst();
        }
    }

    public Optional<User> findByEmail(String email) {
        if (email == null || email.isBlank()) {
            return Optional.empty();
        }

        String normalized = email.trim().toLowerCase();
        synchronized (monitor) {
            return readStore().users.stream()
                    .filter(user -> normalized.equalsIgnoreCase(user.getEmail()))
                    .findFirst();
        }
    }

    public Optional<User> findByUsernameOrEmail(String usernameOrEmail) {
        if (usernameOrEmail == null || usernameOrEmail.isBlank()) {
            return Optional.empty();
        }

        String normalized = usernameOrEmail.trim();
        String normalizedEmail = normalized.toLowerCase();
        synchronized (monitor) {
            return readStore().users.stream()
                    .filter(user -> normalized.equalsIgnoreCase(user.getUsername())
                            || normalizedEmail.equalsIgnoreCase(user.getEmail()))
                    .findFirst();
        }
    }

    public Optional<User> findByFaceEmbeddingsJson(String faceEmbeddingsJson) {
        if (faceEmbeddingsJson == null || faceEmbeddingsJson.isBlank()) {
            return Optional.empty();
        }

        synchronized (monitor) {
            return readStore().users.stream()
                    .filter(user -> faceEmbeddingsJson.equals(user.getFaceEmbeddingsJson()))
                    .findFirst();
        }
    }

    public List<User> findActiveUsersWithFaceEmbeddings() {
        synchronized (monitor) {
            return readStore().users.stream()
                    .filter(User::isActive)
                    .filter(user -> user.getFaceEmbeddingsJson() != null && !user.getFaceEmbeddingsJson().isBlank())
                    .toList();
        }
    }

    public User saveUser(User user) {
        synchronized (monitor) {
            StoreDocument document = readStore();
            List<User> users = new ArrayList<>(document.users);

            if (user.getId() == null) {
                user.setId(nextUserId(users));
            }
            if (user.getRegistrationTimestamp() == null) {
                user.setRegistrationTimestamp(System.currentTimeMillis());
            }

            users.removeIf(existing -> user.getId().equals(existing.getId()));
            users.add(user);
            users.sort(Comparator.comparing(User::getId));

            document.users = users;
            writeStore(document);
            return user;
        }
    }

    public void deleteUserById(Long id) {
        if (id == null) {
            return;
        }

        synchronized (monitor) {
            StoreDocument document = readStore();
            document.users.removeIf(user -> id.equals(user.getId()));
            writeStore(document);
        }
    }

    public void deleteAllUsers() {
        synchronized (monitor) {
            StoreDocument document = readStore();
            document.users = new ArrayList<>();
            writeStore(document);
        }
    }

    public UserBanLog saveBanLog(UserBanLog log) {
        synchronized (monitor) {
            StoreDocument document = readStore();
            List<UserBanLog> banLogs = new ArrayList<>(document.banLogs);

            if (log.getId() == null) {
                log.setId(nextBanLogId(banLogs));
            }
            if (log.getBannedAt() == null) {
                log.setBannedAt(System.currentTimeMillis());
            }

            banLogs.add(log);
            banLogs.sort(Comparator.comparing(UserBanLog::getId));
            document.banLogs = banLogs;
            writeStore(document);
            return log;
        }
    }

    public List<UserBanLog> findAllBanLogs() {
        synchronized (monitor) {
            List<UserBanLog> logs = new ArrayList<>(readStore().banLogs);
            logs.sort(Comparator.comparing(UserBanLog::getBannedAt).reversed());
            return logs;
        }
    }

    public Path getStorePath() {
        return storePath;
    }

    public void seedStoreIfEmpty(List<User> users, List<UserBanLog> banLogs) {
        synchronized (monitor) {
            StoreDocument current = readStore();
            if (!current.users.isEmpty() || !current.banLogs.isEmpty()) {
                return;
            }
            if ((users == null || users.isEmpty()) && (banLogs == null || banLogs.isEmpty())) {
                return;
            }

            StoreDocument seeded = new StoreDocument();
            seeded.users = users == null ? new ArrayList<>() : new ArrayList<>(users);
            seeded.banLogs = banLogs == null ? new ArrayList<>() : new ArrayList<>(banLogs);
            writeStore(seeded);
        }
    }

    private void ensureStoreExists() {
        synchronized (monitor) {
            try {
                Files.createDirectories(storePath.getParent());
                if (!Files.exists(storePath)) {
                    writeStore(new StoreDocument());
                }
            } catch (IOException ex) {
                throw new IllegalStateException("Cannot initialize user store file: " + storePath, ex);
            }
        }
    }

    private StoreDocument readStore() {
        try {
            if (!Files.exists(storePath) || Files.size(storePath) == 0L) {
                return new StoreDocument();
            }
            return objectMapper.readValue(storePath.toFile(), StoreDocument.class);
        } catch (IOException ex) {
            throw new IllegalStateException("Cannot read user store file: " + storePath, ex);
        }
    }

    private void writeStore(StoreDocument document) {
        try {
            Files.createDirectories(storePath.getParent());
            objectMapper.writeValue(storePath.toFile(), document);
        } catch (IOException ex) {
            throw new IllegalStateException("Cannot write user store file: " + storePath, ex);
        }
    }

    private long nextUserId(List<User> users) {
        return users.stream()
                .map(User::getId)
                .filter(id -> id != null)
                .max(Long::compareTo)
                .orElse(0L) + 1L;
    }

    private long nextBanLogId(List<UserBanLog> logs) {
        return logs.stream()
                .map(UserBanLog::getId)
                .filter(id -> id != null)
                .max(Long::compareTo)
                .orElse(0L) + 1L;
    }

    private Path resolveStorePath(String configuredPath) {
        if (configuredPath != null && !configuredPath.isBlank()) {
            return Paths.get(configuredPath).toAbsolutePath().normalize();
        }

        String jpackageAppPath = System.getProperty("jpackage.app-path");
        if (jpackageAppPath != null && !jpackageAppPath.isBlank()) {
            Path appExecutable = Paths.get(jpackageAppPath).toAbsolutePath().normalize();
            Path appRoot = appExecutable.getParent();
            if (appRoot != null) {
                return appRoot.resolve("users.txt");
            }
        }

        Path current = Paths.get("").toAbsolutePath().normalize();
        Path resolved = findAipaAppDirectory(current);
        if (resolved != null) {
            return resolved.resolve("users.txt");
        }

        return current.resolve("users.txt");
    }

    private Path findAipaAppDirectory(Path start) {
        Path current = start;
        while (current != null) {
            if (current.getFileName() != null && "AIPA_App".equalsIgnoreCase(current.getFileName().toString())) {
                return current;
            }

            Path candidate = current.resolve("AIPA_App");
            if (Files.isDirectory(candidate)) {
                return candidate;
            }

            current = current.getParent();
        }
        return null;
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    private static class StoreDocument {
        public List<User> users = new ArrayList<>();
        public List<UserBanLog> banLogs = new ArrayList<>();
    }
}
