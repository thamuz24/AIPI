package com.example.aipa.desktop;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;

@Slf4j
@Component
@ConditionalOnProperty(name = "aipa.controll.autostart", havingValue = "true")
public class ControllServiceAutoStarter {

    private static final Duration HEALTH_TIMEOUT = Duration.ofMillis(700);

    @Value("${aipa.desktop.controll-script:app/controll/run_aipa_all.bat}")
    private String controllScript;

    @EventListener(ApplicationReadyEvent.class)
    public void onReady() {
        if (!isWindows()) {
            return;
        }
        if (isControllServiceHealthy()) {
            return;
        }

        Path scriptPath = resolveScriptPath(controllScript);
        if (scriptPath == null) {
            log.warn("Controll autostart enabled but startup script was not found. Value={}", controllScript);
            return;
        }

        try {
            ProcessBuilder pb = new ProcessBuilder("cmd.exe", "/c", scriptPath.toString());
            pb.directory(scriptPath.getParent().toFile());
            pb.redirectErrorStream(true);
            Process p = pb.start();
            log.info("Started controll service via {}", scriptPath);
            // Let DesktopModeLauncher (if enabled) stream logs; here we just avoid blocking.
        } catch (IOException e) {
            log.warn("Failed to start controll service: {}", e.getMessage());
        }
    }

    private static Path resolveScriptPath(String rawPath) {
        if (rawPath == null || rawPath.isBlank()) {
            return null;
        }
        try {
            Path p = Path.of(rawPath.trim()).toAbsolutePath().normalize();
            if (Files.isRegularFile(p)) {
                return p;
            }
        } catch (Exception ignored) {
        }

        // Fall back to user.dir relative resolution.
        try {
            Path root = Path.of(System.getProperty("user.dir")).toAbsolutePath().normalize();
            Path rel = root.resolve(rawPath.trim()).normalize();
            if (Files.isRegularFile(rel)) {
                return rel;
            }
        } catch (Exception ignored) {
        }

        return null;
    }

    private static boolean isControllServiceHealthy() {
        // The bundled UI expects controll on 127.0.0.1:8001.
        try {
            URL url = new URL("http://127.0.0.1:8001/health");
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout((int) HEALTH_TIMEOUT.toMillis());
            conn.setReadTimeout((int) HEALTH_TIMEOUT.toMillis());
            int code = conn.getResponseCode();
            return code >= 200 && code < 300;
        } catch (Exception ignored) {
            return false;
        }
    }

    private static boolean isWindows() {
        String os = System.getProperty("os.name", "").toLowerCase();
        return os.contains("win");
    }
}

