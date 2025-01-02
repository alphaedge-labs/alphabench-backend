import logging
import json
from datetime import datetime
from typing import Any, Dict
import sys
from pythonjsonlogger import jsonlogger

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Add log level
        log_record['level'] = record.levelname
        
        # Add module/function info
        log_record['module'] = record.module
        log_record['function'] = record.funcName
        
        # Add correlation ID if available
        if hasattr(record, 'correlation_id'):
            log_record['correlation_id'] = record.correlation_id

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance"""
    logger = logging.getLogger(name)
    
    # Only add handlers if they haven't been added yet
    if not logger.handlers:
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        
        # Create formatter
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(module)s %(function)s %(message)s'
        )
        
        # Set formatter for handler
        console_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(console_handler)
        
        # Set log level (can be configured via environment variable)
        logger.setLevel(logging.INFO)
    
    return logger

# Create a filter to add correlation ID
class CorrelationIdFilter(logging.Filter):
    def __init__(self, correlation_id: str):
        super().__init__()
        self.correlation_id = correlation_id
    
    def filter(self, record):
        record.correlation_id = self.correlation_id
        return True
