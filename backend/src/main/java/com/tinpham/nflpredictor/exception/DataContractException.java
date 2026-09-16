package com.tinpham.nflpredictor.exception;

public class DataContractException extends RuntimeException {
    public DataContractException(String message) {
        super(message);
    }

    public DataContractException(String message, Throwable cause) {
        super(message, cause);
    }
}
