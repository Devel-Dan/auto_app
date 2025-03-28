import logging
import os
import sys
from datetime import datetime

def setup_logger(name, log_level=logging.INFO, log_file=None, log_format=None, add_timestamp=True):
    """
    Set up a logger that outputs to both console and file if specified.
    
    Args:
        name (str): Logger name
        log_level (int): Logging level (default: logging.INFO)
        log_file (str, optional): Path to log file (default: None)
        log_format (str, optional): Log format string (default: None)
        add_timestamp (bool): Add timestamp to log filename (default: True)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    
    # Clear any existing handlers to avoid duplicates when reconfiguring
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Set logger level - this is crucial!
    logger.setLevel(log_level)
    
    # Create formatter
    if log_format is None:
        log_format = '%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s'
    formatter = logging.Formatter(log_format, datefmt='%Y-%m-%d %H:%M:%S')
    
    # Create console handler (for stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    
    # Add console handler to logger
    logger.addHandler(console_handler)
    
    # If log file is specified, create file handler
    if log_file:
        # Add timestamp to log filename if requested
        if add_timestamp:
            # Get the current timestamp in a format suitable for filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Split the log file path and add timestamp before the extension
            log_dir = os.path.dirname(log_file)
            log_file_base = os.path.basename(log_file)
            if '.' in log_file_base:
                name, ext = os.path.splitext(log_file_base)
                timestamped_file = f"{name}_{timestamp}{ext}"
            else:
                timestamped_file = f"{log_file_base}_{timestamp}"
                
            # Combine directory and timestamped filename
            if log_dir:
                log_file = os.path.join(log_dir, timestamped_file)
            else:
                log_file = timestamped_file
                
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Create file handler
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        
        # Log the actual filename being used
        logger.info(f"Logging to file: {os.path.abspath(log_file)}")
        
        # Add file handler to logger
        logger.addHandler(file_handler)
    
    # Prevent propagation to the root logger to avoid duplicate logs
    logger.propagate = False
    
    # Log a test message to verify configuration
    logger.debug(f"Logger '{name}' configured with level={logging.getLevelName(log_level)}, file={log_file}")
    
    return logger

# Configure the root logger as well for any uncaught logs
def setup_root_logger(log_level=logging.INFO, log_file=None, log_format=None, add_timestamp=True):
    """Configure the root logger to catch any logs not caught by specific loggers"""
    root_logger = logging.getLogger()
    
    # Clear any existing handlers
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    
    # Set the root logger level
    root_logger.setLevel(log_level)
    
    # Create and add handlers similar to setup_logger
    if log_format is None:
        log_format = '%(asctime)s | %(levelname)-8s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s() | %(message)s'
    formatter = logging.Formatter(log_format, datefmt='%Y-%m-%d %H:%M:%S')
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        # Add timestamp to log filename if requested
        if add_timestamp:
            # Get the current timestamp in a format suitable for filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Split the log file path and add timestamp before the extension
            log_dir = os.path.dirname(log_file)
            log_file_base = os.path.basename(log_file)
            if '.' in log_file_base:
                name, ext = os.path.splitext(log_file_base)
                timestamped_file = f"{name}_{timestamp}{ext}"
            else:
                timestamped_file = f"{log_file_base}_{timestamp}"
                
            # Combine directory and timestamped filename
            if log_dir:
                log_file = os.path.join(log_dir, timestamped_file)
            else:
                log_file = timestamped_file
        
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        
        # Log the actual filename being used
        root_logger.info(f"Root logger writing to file: {os.path.abspath(log_file)}")
        
        root_logger.addHandler(file_handler)
    
    return root_logger

# Example usage:
if __name__ == "__main__":
    # Create a session timestamp once for the entire run
    session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Set up root logger first to capture all logs
    setup_root_logger(
        log_level=logging.DEBUG, 
        log_file=f"logs/all_logs.log",
        add_timestamp=True  # Will create e.g., all_logs_20250327_123456.log
    )
    
    # Set up a specific logger with the same timestamp
    test_logger = setup_logger(
        "test_logger", 
        log_level=logging.DEBUG, 
        log_file=f"logs/test.log",
        add_timestamp=True
    )
    
    # Log session start
    test_logger.info(f"=== New Session Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    
    # Test logging at different levels
    test_logger.debug("This is a debug message")
    test_logger.info("This is an info message")
    test_logger.warning("This is a warning message")
    test_logger.error("This is an error message")
    test_logger.critical("This is a critical message")
    
    # Test logging from a different module
    other_logger = logging.getLogger("other_module")
    other_logger.warning("This warning should be caught by the root logger")
    
    # Log session end
    test_logger.info(f"=== Session Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")