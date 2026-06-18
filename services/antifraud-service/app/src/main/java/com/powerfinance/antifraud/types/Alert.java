package com.powerfinance.antifraud.types;

public class Alert {
    public String clerkId;
    public String message;

    public Alert() {}

    public Alert(String clerkId, String message) {
        this.clerkId = clerkId;
        this.message = message;
    }

    @Override
    public String toString() {
        return message;
    }
}
