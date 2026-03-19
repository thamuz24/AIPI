package com.example.aipa;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

import java.awt.Desktop;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.URI;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.List;

@SpringBootApplication
public class AipaApplication {

	private static FileChannel instanceLockChannel;
	private static FileLock instanceLock;

	public static void main(String[] args) {
		configurePackagedPaths();
		if (shouldExitBecauseInstanceAlreadyRunning()) {
			return;
		}
		autostartControllServiceEarly();
		SpringApplication.run(AipaApplication.class, args);
	}

	private static void autostartControllServiceEarly() {
		// Start the Python controll service as early as possible so the UI doesn't hit "cannot connect" on first prompts.
		boolean enabled = Boolean.parseBoolean(System.getProperty("aipa.controll.autostart", "false"));
		if (!enabled) {
			String env = System.getenv("AIPA_CONTROLL_AUTOSTART");
			enabled = env != null && (env.equalsIgnoreCase("1") || env.equalsIgnoreCase("true") || env.equalsIgnoreCase("yes"));
		}
		if (!enabled) {
			return;
		}
		if (!System.getProperty("os.name", "").toLowerCase().contains("win")) {
			return;
		}
		// If something is already listening on 8001, don't try to start another copy.
		if (!isPortAvailable(8001)) {
			return;
		}

		String script = System.getProperty("aipa.desktop.controll-script", "app/controll/run_aipa_all.bat");
		try {
			Path scriptPath = Path.of(script).toAbsolutePath().normalize();
			if (!Files.isRegularFile(scriptPath)) {
				// Try resolving relative to detected app root (works for dev runs too).
				Path appRoot = detectAppRoot();
				if (appRoot != null) {
					Path rel = appRoot.resolve(script).normalize();
					if (Files.isRegularFile(rel)) {
						scriptPath = rel;
					}
				}
			}
			if (!Files.isRegularFile(scriptPath)) {
				return;
			}

			ProcessBuilder pb = new ProcessBuilder("cmd.exe", "/c", scriptPath.toString());
			pb.directory(scriptPath.getParent().toFile());
			pb.redirectErrorStream(true);
			pb.start();
		} catch (Exception ignored) {
			// Best-effort only; DesktopModeLauncher/ControllServiceAutoStarter will try again later.
		}
	}

	private static void configurePackagedPaths() {
		boolean hasCustomStaticLocations = System.getProperty("AIPA_STATIC_LOCATIONS") != null
				|| System.getenv("AIPA_STATIC_LOCATIONS") != null;
		boolean hasCustomControllScript = System.getProperty("aipa.desktop.controll-script") != null
				|| System.getenv("AIPA_DESKTOP_CONTROLL_SCRIPT") != null;
		boolean hasCustomControllAutostart = System.getProperty("aipa.controll.autostart") != null
				|| System.getenv("AIPA_CONTROLL_AUTOSTART") != null;

		Path appRoot = detectAppRoot();
		if (appRoot == null) {
			return;
		}

		if (!hasCustomStaticLocations) {
			Path clientDir = appRoot.resolve("app").resolve("client").normalize();
			if (Files.isDirectory(clientDir)) {
				System.setProperty(
						"AIPA_STATIC_LOCATIONS",
						clientDir.toUri() + ",classpath:/static/,classpath:/public/,classpath:/resources/,classpath:/META-INF/resources/"
				);
			}
		}

		if (!hasCustomControllScript) {
			Path controllScript = appRoot.resolve("app").resolve("controll").resolve("run_aipa_all.bat").normalize();
			if (Files.isRegularFile(controllScript)) {
				System.setProperty("aipa.desktop.controll-script", controllScript.toString());
			}
		}

		if (!hasCustomControllAutostart) {
			Path controllScript = appRoot.resolve("app").resolve("controll").resolve("run_aipa_all.bat").normalize();
			if (Files.isRegularFile(controllScript)) {
				System.setProperty("aipa.controll.autostart", "true");
			}
		}
	}

	private static Path detectAppRoot() {
		Path fromClasspath = detectAppRootFromClasspath();
		if (fromClasspath != null) {
			return fromClasspath;
		}

		String jpackageAppPath = System.getProperty("jpackage.app-path");
		if (jpackageAppPath != null && !jpackageAppPath.isBlank()) {
			try {
				Path launcher = Path.of(jpackageAppPath).toAbsolutePath().normalize();
				Path parent = launcher.getParent();
				if (parent != null) {
					return parent;
				}
			} catch (Exception ignored) {
				// Fallback below.
			}
		}

		try {
			return Path.of(System.getProperty("user.dir")).toAbsolutePath().normalize();
		} catch (Exception ignored) {
			return null;
		}
	}

	private static Path detectAppRootFromClasspath() {
		String classPath = System.getProperty("java.class.path");
		if (classPath == null || classPath.isBlank()) {
			return null;
		}

		String firstEntry = classPath;
		int sep = classPath.indexOf(java.io.File.pathSeparatorChar);
		if (sep >= 0) {
			firstEntry = classPath.substring(0, sep);
		}

		try {
			Path entryPath = Path.of(firstEntry).toAbsolutePath().normalize();
			if (Files.isRegularFile(entryPath)) {
				Path parent = entryPath.getParent(); // .../app
				if (parent != null) {
					Path appRoot = parent.getParent(); // .../
					if (appRoot != null) {
						return appRoot;
					}
				}
			}
		} catch (Exception ignored) {
			return null;
		}

		return null;
	}

	private static boolean shouldExitBecauseInstanceAlreadyRunning() {
		int port = getIntSetting("server.port", "SERVER_PORT", 8080);
		if (!acquireSingleInstanceLock(port)) {
			String appUrl = "http://127.0.0.1:" + port;
			if (!isPortAvailable(port)) {
				openUrl(appUrl);
			}
			System.out.println("AIPA is already running. Opening existing UI if available.");
			return true;
		}

		if (isPortAvailable(port)) {
			return false;
		}

		String appUrl = "http://127.0.0.1:" + port;
		openUrl(appUrl);
		System.out.println("AIPA server port is already in use. Opening existing UI.");
		return true;
	}

	private static boolean acquireSingleInstanceLock(int port) {
		try {
			Path lockPath = Path.of(System.getProperty("java.io.tmpdir"), "aipa-instance-" + port + ".lock");
			instanceLockChannel = FileChannel.open(lockPath, StandardOpenOption.CREATE, StandardOpenOption.WRITE);
			instanceLock = instanceLockChannel.tryLock();
			if (instanceLock == null) {
				closeInstanceLockChannelQuietly();
				return false;
			}
			Runtime.getRuntime().addShutdownHook(new Thread(AipaApplication::releaseInstanceLockQuietly, "aipa-instance-lock-release"));
			return true;
		} catch (OverlappingFileLockException ignored) {
			closeInstanceLockChannelQuietly();
			return false;
		} catch (Exception ignored) {
			closeInstanceLockChannelQuietly();
			return false;
		}
	}

	private static void releaseInstanceLockQuietly() {
		try {
			if (instanceLock != null && instanceLock.isValid()) {
				instanceLock.release();
			}
		} catch (Exception ignored) {
			// Ignore
		} finally {
			closeInstanceLockChannelQuietly();
		}
	}

	private static void closeInstanceLockChannelQuietly() {
		try {
			if (instanceLockChannel != null && instanceLockChannel.isOpen()) {
				instanceLockChannel.close();
			}
		} catch (Exception ignored) {
			// Ignore
		}
		instanceLockChannel = null;
		instanceLock = null;
	}

	private static boolean getBooleanSetting(String systemProperty, String envVariable, boolean defaultValue) {
		String fromSystemProperty = System.getProperty(systemProperty);
		if (fromSystemProperty != null) {
			return Boolean.parseBoolean(fromSystemProperty);
		}

		String fromEnv = System.getenv(envVariable);
		if (fromEnv != null) {
			return Boolean.parseBoolean(fromEnv);
		}

		return defaultValue;
	}

	private static int getIntSetting(String systemProperty, String envVariable, int defaultValue) {
		String fromSystemProperty = System.getProperty(systemProperty);
		if (fromSystemProperty != null) {
			try {
				return Integer.parseInt(fromSystemProperty);
			} catch (NumberFormatException ignored) {
				return defaultValue;
			}
		}

		String fromEnv = System.getenv(envVariable);
		if (fromEnv != null) {
			try {
				return Integer.parseInt(fromEnv);
			} catch (NumberFormatException ignored) {
				return defaultValue;
			}
		}

		return defaultValue;
	}

	private static boolean isPortAvailable(int port) {
		try (ServerSocket socket = new ServerSocket()) {
			socket.setReuseAddress(false);
			socket.bind(new InetSocketAddress("127.0.0.1", port));
			return true;
		} catch (Exception ignored) {
			return false;
		}
	}

	private static void openUrl(String url) {
		try {
			String edgeExe = detectEdgeExecutable();
			if (edgeExe != null) {
				new ProcessBuilder(edgeExe, "--app=" + url, "--window-size=1280,820", "--window-position=120,80").start();
				return;
			}
		} catch (Exception ignored) {
			// Fallback to default browser below.
		}

		try {
			if (Desktop.isDesktopSupported()) {
				Desktop.getDesktop().browse(URI.create(url));
				return;
			}
		} catch (Exception ignored) {
			// Fallback below.
		}

		try {
			new ProcessBuilder("cmd.exe", "/c", "start", "", url).start();
		} catch (Exception ignored) {
			// Keep silent: we still exit gracefully when another instance is already running.
		}
	}

	private static String detectEdgeExecutable() {
		List<String> candidates = new ArrayList<>();
		String pf = System.getenv("ProgramFiles");
		String pfx86 = System.getenv("ProgramFiles(x86)");
		String localAppData = System.getenv("LocalAppData");

		if (pf != null && !pf.isBlank()) {
			candidates.add(pf + "\\Microsoft\\Edge\\Application\\msedge.exe");
		}
		if (pfx86 != null && !pfx86.isBlank()) {
			candidates.add(pfx86 + "\\Microsoft\\Edge\\Application\\msedge.exe");
		}
		if (localAppData != null && !localAppData.isBlank()) {
			candidates.add(localAppData + "\\Microsoft\\Edge\\Application\\msedge.exe");
		}

		for (String candidate : candidates) {
			try {
				Path path = Path.of(candidate).toAbsolutePath().normalize();
				if (Files.isRegularFile(path)) {
					return path.toString();
				}
			} catch (Exception ignored) {
				// Continue scanning other candidates.
			}
		}
		return null;
	}

}
