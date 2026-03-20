package com.example.aipa.controller;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/face")
public class FaceProxyController {

    private final HttpClient httpClient;

    @Value("${aipa.controll.base-url:http://127.0.0.1:8001}")
    private String controllBaseUrl;

    public FaceProxyController() {
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(4))
                .build();
    }

    @PostMapping(value = "/extract", produces = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<String> extractFaceEmbedding(@RequestBody(required = false) String body) {
        String payload = (body == null || body.isBlank()) ? "{}" : body;
        URI target = URI.create(trimTrailingSlash(controllBaseUrl) + "/api/face/extract");

        HttpRequest request = HttpRequest.newBuilder(target)
                .timeout(Duration.ofSeconds(35))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(payload, StandardCharsets.UTF_8))
                .build();

        try {
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
            String contentType = response.headers().firstValue("content-type").orElse(MediaType.APPLICATION_JSON_VALUE);
            return ResponseEntity.status(response.statusCode())
                    .contentType(MediaType.parseMediaType(contentType))
                    .body(response.body());
        } catch (Exception e) {
            String message = "Cannot reach aipa_controll at " + trimTrailingSlash(controllBaseUrl) + " (expected /api/face/extract).";
            return ResponseEntity.status(503)
                    .contentType(MediaType.APPLICATION_JSON)
                    .body("{\"message\":\"" + jsonEscape(message) + "\"}");
        }
    }

    private static String trimTrailingSlash(String value) {
        if (value == null) return "";
        return value.endsWith("/") ? value.substring(0, value.length() - 1) : value;
    }

    private static String jsonEscape(String value) {
        if (value == null) return "";
        // Minimal JSON string escape (enough for our error message).
        return value
                .replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\r", "\\r")
                .replace("\n", "\\n");
    }
}

