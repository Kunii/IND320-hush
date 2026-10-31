"""
    src/utils/env.py
    
    Provides a SecretManager for loading secrets from TOML.
    
"""

import tomllib
import streamlit as st
from pathlib import Path
from typing import Any

class SecretManager:
    
    def __init__(self, secrets_path: Path | str | None = None, local_priority: bool = False, path_redacted: bool = True) -> None:
        
        self._repo_root: Path = Path(__file__).parent.parent.parent # Fetch repo root directory
        self._secrets_path: Path = self._repo_root / ".secrets" # Define secrets dir
        self._local_priority: bool = local_priority # Flag to determine if local secrets have priority
        self._path_redacted: bool = path_redacted # Flag to determine if secrets path should be redacted in logs
        
        self._data: dict[str, Any] = {} # Initialize an empty dictionary to hold secrets
        
        self.file_path: Path = self._resolve_secrets_path(secrets_path) # Resolve the secrets file path
        self._load_secrets() # Load secrets from the specified file
    
    
    def _resolve_secrets_path(self, secrets_path: Path | str | None = None) -> Path:
        """
            Resolves secrets path to a path object.
            
            Args:
                secrets_path (Path | str | None): The path to the secrets file. If None, defaults to "secrets.toml" in the repo root.
            
            Returns:
                Path: Absolute path to the secrets file.
        """
        
        if secrets_path is not None: # Check if a secrets file path is provided
            file_path = Path(secrets_path)
            if self._path_redacted:
                print(f"Using secrets path: {str(file_path).replace(str(self._repo_root.parent), '[REDACTED]')}")
            else:
                print(f"Using secrets path: {file_path}")
        else:
            file_path = self._secrets_path / "secrets.toml" # Construct default path to secrets.toml
            
            if self._path_redacted:
                print(f"No secrets path provided")
                print(f"Defaulting to: {str(file_path).replace(str(self._repo_root.parent), '[REDACTED]')}")
            else:
                print(f"No secrets path provided")
                print(f"Defaulting to: {file_path}")
        
        return file_path


    def _load_secrets(self) -> None:
        """
            Loads secrets into memory as a dictionary.

            Local development uses .secrets/secrets.toml. Streamlit Community
            Cloud has no such file, so st.secrets is used as a fallback (and
            merged on top of the local file when both are available).
        """

        self._data = {}

        if self.file_path.exists():
            with open(self.file_path, "rb") as f:
                self._data = tomllib.load(f)
        else:
            print(f"Local secrets file not found at: {self.file_path}")

        try: # Merge Streamlit secrets when running inside Streamlit
            sl_dict = {k: v for k, v in st.secrets.items()}
            if sl_dict:
                self._data = self._merge_secrets(sl_dict)
                print("Loaded secrets from Streamlit & merged with local secrets.")
        except Exception:
            pass # No Streamlit secrets available (plain Python / notebook)

        if not self._data:
            raise FileNotFoundError(
                "No secrets found. Provide .secrets/secrets.toml locally or "
                "configure the secrets in Streamlit."
            )

    
    def _merge_secrets(self, streamlit_secrets: dict[str, Any]) -> dict[str, Any]:
        """
            Merges secrets from Streamlit with local secrets.
            
            Args:
                streamlit_secrets (dict[str, Any]): Secrets from Streamlit.
                local_priority (bool): If True, local secrets will override Streamlit secrets. Default is False.
            
            Returns:
                dict[str, Any]: Merged dictionary of secrets.
        """
        
        print(f"Merging secrets with local priority: {self._local_priority}")
        merged = self._data.copy()
        
        for key, value in streamlit_secrets.items():
            if self._local_priority and key in merged:
                continue # Skip if local secrets have priority and key exists in local secrets
            
            merged[key] = value # Update or add the secret from Streamlit
        
        return merged

    def unpack_nested_dicts(self, unpack_dict: dict) -> dict:
        """
            Unpacks nested dictionaries into a flat dictionary.
            
            Args:
                unpack_dict (dict): The dictionary to unpack.
            
            Returns:
                dict: A flat dictionary with nested keys represented in dot notation.
        """
        
        flat_dict = {}
        
        for key, value in unpack_dict.items():
            
            if isinstance(value, dict):
                nested_flat = self.unpack_nested_dicts(value)
                
                for sub_key, sub_value in nested_flat.items():
                    flat_dict[f"{key}.{sub_key}"] = sub_value
                    #print(f"Unpacked nested key: {key}.{sub_key} -> {sub_value}")
                    
            else:
                flat_dict[key] = value
        
        return flat_dict

    def get(self, key:str, default: Any = None) -> Any:
        """
            Retrieves secret value by key.
            
            Args:
                key (str): Secret key to look up. Traverses nested dictionaries using dot notation (e.g. "parent.child.key").
                default (Any): Default return value is key is not found. Default is None.
            
            Returns:
                Any: Value of the secret, or the default value if not found.
        """
        
        return self._data.get(key, self.unpack_nested_dicts(self._data).get(key, default))
    
    def get_required(self, key:str) -> Any:
        """
            Retrieves a required secret value by key.
            
            Args:
                key (str): Secret key to look up. Supports flat keys (nested dicts, e.g. "parent.child.key").
        
            Returns:
                Any: Value of the secret.
            
            Raises:
                KeyError: If the key is not found.
        """
        value = self.get(key)
        
        if value is None:
            raise KeyError(f"Required secret not found: {key}")
        
        return value


    def dump_secrets_raw(self) -> None:
        """
            !! DANGER !!
            
            Debug ONLY:
                Dumps loaded secrets to console.
                
            !! DANGER !!
        """
        
        print("Loaded Secrets (Raw):")
        
        for key, value in self._data.items():
            print(f"    {key}: {value}")
    
    
    def dump_secrets(self) -> None:
        """
            !! DANGER !!
            
            Debug ONLY:
                Dumps loaded secrets in a flat format (unpacked nested dicts) to console.
                
            !! DANGER !!
        """
        
        print("Loaded Secrets (Unpacked):")

        for key, value in self.unpack_nested_dicts(self._data).items():
                print(f"    {key}: {value}")
    
secrets = SecretManager() # Init as singleton for global access
#secrets.dump_secrets_raw()
#secrets.dump_secrets()
#print(f"TEST_SECRET: {secrets.get('TEST_SECRET', 'Not Found')}")
#print(f"inner_dict_key (Required): {secrets.get_required('topDict.subDict.inner_dict_key')}")
#print(f"Test Required (Fails): {secrets.get_required('TEST_SECRET')}")
