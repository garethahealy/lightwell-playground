package com.garethahealy.lightwell.services;

import java.util.logging.Logger;

public class HelloWorldService {

    private final Logger logger;

    public HelloWorldService(Logger logger) {
        this.logger = logger;
    }

    public void hello() {
        logger.info("Hello World!");
    }
}
