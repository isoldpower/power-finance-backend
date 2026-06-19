package com.powerfinance.antifraud.model;

/** Fraud alert emitted for a user, carried as a Flink POJO to the alerts sink. */
public class Alert {
    private String clerkId;
    private String message;

    public Alert() {}

    public Alert(String clerkId, String message) {
        this.clerkId = clerkId;
        this.message = message;
    }

    /** Returns the Clerk id of the user the alert concerns. */
    public String getClerkId() {
        return clerkId;
    }

    /** Sets the Clerk id of the user the alert concerns. */
    public void setClerkId(String clerkId) {
        this.clerkId = clerkId;
    }

    /** Returns the human-readable alert message. */
    public String getMessage() {
        return message;
    }

    /** Sets the human-readable alert message. */
    public void setMessage(String message) {
        this.message = message;
    }

    /** Returns the alert message as the string representation. */
    @Override
    public String toString() {
        return message;
    }
}
