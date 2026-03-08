package com.example.aipa.controller;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.server.ResponseStatusException;

@Controller
public class SpaForwardController {

    @GetMapping(value = {
            "/",
            "/{path:[^\\.]*}",
            "/{path:[^\\.]*}/{subpath:[^\\.]*}"
    })
    public String forwardToIndex(HttpServletRequest request) {
        String requestUri = request.getRequestURI();
        if (requestUri.startsWith("/api/")) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND);
        }
        return "forward:/index.html";
    }
}
