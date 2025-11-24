"""Configuration management for the video converter."""

import json
import logging
from pathlib import Path
from typing import List


class ConfigurationError(Exception):
    """Exception raised for configuration-related errors."""
    pass


class ConfigManager:
    """Manages loading and validation of configuration from config.json."""
    
    REQUIRED_FIELDS = [
        "compress",
        "delete_mp4",
        "output_directory_path",
        "input_directory_path"
    ]
    
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize ConfigManager with path to configuration file.
        
        Args:
            config_path: Path to the JSON configuration file (default: "config.json")
        """
        self.config_path = Path(config_path)
        self._config = None
        self._load_and_validate()
    
    def _load_and_validate(self):
        """Load and validate configuration on initialization."""
        try:
            logging.info(f"Loading configuration from {self.config_path}")
            self._config = self.load_config()
            if not self.validate_config(self._config):
                raise ConfigurationError("Configuration validation failed")
            logging.info("Configuration loaded and validated successfully")
        except ConfigurationError:
            logging.error(f"Configuration error: Failed to load or validate {self.config_path}")
            raise
        except Exception as e:
            logging.error(f"Unexpected error loading configuration: {e}")
            raise ConfigurationError(f"Unexpected error loading configuration: {e}")
    
    def load_config(self) -> dict:
        """
        Read and parse JSON configuration from file.
        
        Returns:
            Dictionary containing configuration data
            
        Raises:
            ConfigurationError: If file is missing or contains invalid JSON
        """
        try:
            if not self.config_path.exists():
                error_msg = f"Configuration file not found: {self.config_path}"
                logging.error(error_msg)
                raise ConfigurationError(error_msg)
            
            logging.debug(f"Reading configuration file: {self.config_path}")
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            logging.info(f"Configuration loaded from {self.config_path}")
            logging.debug(f"Configuration contents: {config}")
            return config
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in configuration file: {e}"
            logging.error(error_msg)
            raise ConfigurationError(error_msg)
        except ConfigurationError:
            raise
        except Exception as e:
            error_msg = f"Error reading configuration file: {e}"
            logging.error(error_msg)
            raise ConfigurationError(error_msg)
    
    def validate_config(self, config: dict) -> bool:
        """
        Verify that all required fields exist and are valid.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if configuration is valid
            
        Raises:
            ConfigurationError: If validation fails
        """
        try:
            logging.debug("Starting configuration validation")
            
            # Check for missing required fields
            missing_fields = [
                field for field in self.REQUIRED_FIELDS 
                if field not in config
            ]
            
            if missing_fields:
                error_msg = f"Missing required configuration fields: {', '.join(missing_fields)}"
                logging.error(error_msg)
                raise ConfigurationError(error_msg)
            
            logging.debug("All required fields present")
            
            # Validate boolean fields
            if not isinstance(config["compress"], bool):
                error_msg = f"'compress' must be a boolean, got {type(config['compress']).__name__}"
                logging.error(error_msg)
                raise ConfigurationError(error_msg)
            
            if not isinstance(config["delete_mp4"], bool):
                error_msg = f"'delete_mp4' must be a boolean, got {type(config['delete_mp4']).__name__}"
                logging.error(error_msg)
                raise ConfigurationError(error_msg)
            
            logging.debug("Boolean fields validated")
            
            # Validate directory paths
            if not isinstance(config["input_directory_path"], str):
                error_msg = f"'input_directory_path' must be a string, got {type(config['input_directory_path']).__name__}"
                logging.error(error_msg)
                raise ConfigurationError(error_msg)
            
            if not isinstance(config["output_directory_path"], str):
                error_msg = f"'output_directory_path' must be a string, got {type(config['output_directory_path']).__name__}"
                logging.error(error_msg)
                raise ConfigurationError(error_msg)
            
            logging.debug("Directory path types validated")
            
            # Validate that input directory exists
            input_path = Path(config["input_directory_path"])
            if not input_path.exists():
                error_msg = f"Input directory does not exist: {input_path}"
                logging.error(error_msg)
                raise ConfigurationError(error_msg)
            
            if not input_path.is_dir():
                error_msg = f"Input path is not a directory: {input_path}"
                logging.error(error_msg)
                raise ConfigurationError(error_msg)
            
            logging.debug(f"Input directory validated: {input_path}")
            
            # Validate that output directory path is valid
            output_path = Path(config["output_directory_path"])
            try:
                if output_path.exists() and not output_path.is_dir():
                    error_msg = f"Output path exists but is not a directory: {output_path}"
                    logging.error(error_msg)
                    raise ConfigurationError(error_msg)
                
                logging.debug(f"Output directory path validated: {output_path}")
                
            except ConfigurationError:
                raise
            except Exception as e:
                error_msg = f"Invalid output directory path: {e}"
                logging.error(error_msg)
                raise ConfigurationError(error_msg)
            
            logging.info("Configuration validation successful")
            return True
            
        except ConfigurationError:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during configuration validation: {e}"
            logging.error(error_msg)
            raise ConfigurationError(error_msg)
    
    @property
    def compress(self) -> bool:
        """Get the compress configuration value."""
        return self._config["compress"]
    
    @property
    def delete_mp4(self) -> bool:
        """Get the delete_mp4 configuration value."""
        return self._config["delete_mp4"]
    
    @property
    def input_directory(self) -> Path:
        """Get the input directory path as a Path object."""
        return Path(self._config["input_directory_path"])
    
    @property
    def output_directory(self) -> Path:
        """Get the output directory path as a Path object."""
        return Path(self._config["output_directory_path"])
    
    @property
    def thumbnail_video_percentage(self) -> List[int]:
        """Get the thumbnail video percentage values."""
        return self._config.get("thumbnail_video_percentage", [30, 50, 70])
