package com.example.aipa.desktop;

import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

import java.awt.Desktop;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;

@Slf4j
@Component
@ConditionalOnProperty(name = "aipa.desktop.enabled", havingValue = "true")
public class DesktopModeLauncher {

    private final ConfigurableApplicationContext context;
    private final AtomicBoolean shuttingDown = new AtomicBoolean(false);

    private final int serverPort;
    private final String controllScriptRelativePath;
    private final boolean openUi;
    private final boolean stopOnUiClose;

    private volatile Process controllProcess;
    private volatile Process uiProcess;

    public DesktopModeLauncher(
            ConfigurableApplicationContext context,
            @Value("${server.port:8080}") int serverPort,
            @Value("${aipa.desktop.controll-script:app/controll/run_aipa_all.bat}") String controllScriptRelativePath,
            @Value("${aipa.desktop.open-ui:true}") boolean openUi,
            @Value("${aipa.desktop.stop-on-ui-close:false}") boolean stopOnUiClose
    ) {
        this.context = context;
        this.serverPort = serverPort;
        this.controllScriptRelativePath = controllScriptRelativePath;
        this.openUi = openUi;
        this.stopOnUiClose = stopOnUiClose;
    }

    @EventListener(ApplicationReadyEvent.class)
    public void onApplicationReady() {
        Runtime.getRuntime().addShutdownHook(new Thread(this::stopManagedProcesses, "aipa-desktop-shutdown"));
        startControllService();
        if (openUi) {
            startDesktopWindowAndBindLifecycle();
        }
    }

    @PreDestroy
    public void onDestroy() {
        stopManagedProcesses();
    }

    private void startControllService() {
        if (!isWindows()) {
            log.warn("Desktop mode controll autostart is only implemented for Windows.");
            return;
        }

        Path appRoot = Path.of(System.getProperty("user.dir")).toAbsolutePath().normalize();
        Path scriptPath = appRoot.resolve(controllScriptRelativePath).normalize();
        if (!Files.exists(scriptPath)) {
            log.warn("Controll startup script not found: {}", scriptPath);
            return;
        }

        try {
            ProcessBuilder pb = new ProcessBuilder("cmd.exe", "/c", scriptPath.toString());
            pb.directory(scriptPath.getParent().toFile());
            pb.redirectErrorStream(true);
            controllProcess = pb.start();
            streamProcessLogs(controllProcess, "controll");
            log.info("Started aipa_controll from {}", scriptPath);
        } catch (IOException e) {
            log.error("Failed to start aipa_controll: {}", e.getMessage());
        }
    }

    private void startDesktopWindowAndBindLifecycle() {
        String appUrl = "http://127.0.0.1:" + serverPort;
        Process edgeProcess = null;

        try {
            String edgeExe = detectEdgeExecutable();
            if (edgeExe != null) {
                List<String> cmd = new ArrayList<>();
                cmd.add(edgeExe);
                cmd.add("--app=" + appUrl);
                cmd.add("--window-size=1280,820");
                cmd.add("--window-position=120,80");
                edgeProcess = new ProcessBuilder(cmd).start();
                uiProcess = edgeProcess;
                log.info("Opened desktop app window via Edge app mode: {}", appUrl);
            } else if (openInDefaultBrowser(appUrl)) {
                log.info("Edge not found. Opened default browser at {}", appUrl);
                return;
            } else {
                log.warn("Cannot open desktop UI: no Edge and browser open fallback failed.");
                return;
            }
        } catch (Exception e) {
            log.warn("Failed to open desktop UI by Edge app mode: {}. Falling back.", e.getMessage());
            if (openInDefaultBrowser(appUrl)) {
                return;
            }
            log.error("Failed to open desktop UI by all methods.");
            return;
        }

        if (!stopOnUiClose) {
            log.info("UI close watcher is disabled (aipa.desktop.stop-on-ui-close=false).");
            return;
        }

        Process finalEdgeProcess = edgeProcess;
        Thread watcher = new Thread(() -> {
            try {
                if (finalEdgeProcess != null) {
                    finalEdgeProcess.waitFor();
                    log.info("Desktop window was closed. Stopping AIPA services.");
                    requestShutdown();
                }
            } catch (InterruptedException ignored) {
                Thread.currentThread().interrupt();
            }
        }, "aipa-ui-watcher");
        watcher.setDaemon(true);
        watcher.start();
    }

    private void requestShutdown() {
        if (!shuttingDown.compareAndSet(false, true)) {
            return;
        }
        stopManagedProcesses();
        int exitCode = 0;
        try {
            exitCode = org.springframework.boot.SpringApplication.exit(context, () -> 0);
        } catch (Exception e) {
            log.warn("Error while stopping Spring context: {}", e.getMessage());
        }
        System.exit(exitCode);
    }

    private void stopManagedProcesses() {
        stopProcessTree(uiProcess, "ui");
        stopProcessTree(controllProcess, "controll");
    }

    private void stopProcessTree(Process process, String name) {
        if (process == null || !process.isAlive()) {
            return;
        }
        long pid = process.pid();
        try {
            if (isWindows()) {
                new ProcessBuilder("cmd.exe", "/c", "taskkill", "/PID", String.valueOf(pid), "/T", "/F")
                        .start()
                        .waitFor();
            } else {
                process.destroyForcibly();
            }
            log.info("Stopped {} process tree (pid={})", name, pid);
        } catch (Exception e) {
            log.warn("Failed to stop {} process (pid={}): {}", name, pid, e.getMessage());
        }
    }

    private void streamProcessLogs(Process process, String sourceName) {
        Thread t = new Thread(() -> {
            try (BufferedReader br = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = br.readLine()) != null) {
                    log.info("[{}] {}", sourceName, line);
                }
            } catch (IOException ignored) {
            }
        }, "aipa-log-" + sourceName);
        t.setDaemon(true);
        t.start();
    }

    private String detectEdgeExecutable() {
        String pf = System.getenv("ProgramFiles");
        String pfx86 = System.getenv("ProgramFiles(x86)");
        String localAppData = System.getenv("LocalAppData");
        List<String> candidates = List.of(
                pf != null ? pf + "\\Microsoft\\Edge\\Application\\msedge.exe" : null,
                pfx86 != null ? pfx86 + "\\Microsoft\\Edge\\Application\\msedge.exe" : null,
                localAppData != null ? localAppData + "\\Microsoft\\Edge\\Application\\msedge.exe" : null
        );
        for (String path : candidates) {
            if (path == null) {
                continue;
            }
            if (Files.exists(Path.of(path))) {
                return path;
            }
        }
        return null;
    }

    private boolean openInDefaultBrowser(String url) {
        try {
            if (Desktop.isDesktopSupported()) {
                Desktop.getDesktop().browse(URI.create(url));
                return true;
            }
        } catch (Exception ignored) {
            // Try command fallback below.
        }
        try {
            new ProcessBuilder("cmd.exe", "/c", "start", "", url).start();
            return true;
        } catch (Exception ignored) {
            return false;
        }
    }

    private boolean isWindows() {
        String osName = System.getProperty("os.name");
        return osName != null && osName.toLowerCase().contains("win");
    }
}
