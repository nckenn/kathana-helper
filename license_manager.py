"""
License Manager for Kathana Helper
Handles license key generation, validation, and storage using RSA cryptography
"""
import os
import json
import base64
import hashlib
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend


class LicenseManager:
    """Manages license key generation, validation, and storage"""
    
    # License file location
    LICENSE_FILE = "license.json"
    
    # Public key for verification (embedded in the application)
    # This is the public key that corresponds to the private key used for signing
    # In production, this should be generated separately and the private key kept secret
    PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAm7675MGhIECkGMHhdy6M
aDig/mz2kYOpT/yGg78NZxC6UxLQEQqiaiFZISzdJQ+1e0RePmGGReh2GjVhKqmD
rDcofgEsh21zWKtGyA01c6lDc+5O6gepbRM1k9co0Yh9+Sq6qA41qRPKvwsTKwZm
ZmItip0yR9/AUBQ7q0hf1qmRrZo3jwAFgnzwhEtBocrpEyDeDpkYWD1HcLoRAdqN
8odlv4FNp8sH9pKBXuiSCSP4FuG5D3q/FmlHIFo6FUDWilsH1BowVyX/HRn0mVn9
2W0Lajt2ZE0FMNLQEgQucIR1d1VWL3c8ZYsf/QM2ZcIWuAa0KzdNwr2z4GsCAHqV
JQIDAQAB
-----END PUBLIC KEY-----"""
    
    def __init__(self):
        """Initialize the license manager"""
        self.public_key = None
        self._load_public_key()
    
    def _load_public_key(self):
        """Load the public key for verification"""
        try:
            self.public_key = serialization.load_pem_public_key(
                self.PUBLIC_KEY_PEM.encode(),
                backend=default_backend()
            )
        except Exception as e:
            print(f"Error loading public key: {e}")
            self.public_key = None
    
    def _get_machine_id(self):
        """
        Generate a unique machine identifier based on system hardware
        This helps prevent license sharing across different machines
        """
        try:
            import platform
            import uuid
            
            # Get machine-specific identifiers
            machine_name = platform.node()
            mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                                   for elements in range(0, 2*6, 2)][::-1])
            
            # Combine and hash
            machine_string = f"{machine_name}-{mac_address}"
            machine_id = hashlib.sha256(machine_string.encode()).hexdigest()[:16]
            return machine_id
        except Exception:
            # Fallback to a generic ID if detection fails
            return "unknown-machine"
    
    def validate_license(self, license_key=None):
        """
        Validate a license key
        
        Args:
            license_key: License key string (if None, loads from file)
            
        Returns:
            tuple: (is_valid: bool, message: str, license_data: dict)
        """
        if license_key is None:
            # Try to load from file
            license_key = self._load_license_from_file()
            if not license_key:
                return False, "No license key found. Please enter a valid license key.", None
        
        try:
            # Decode the license key
            license_data = self._decode_license(license_key)
            if not license_data:
                return False, "Invalid license key format.", None
            
            # Verify signature
            if not self._verify_signature(license_data):
                return False, "License key signature is invalid. The license may be tampered with.", None
            
            # Check expiration
            if 'expires' in license_data:
                expires_date = datetime.fromisoformat(license_data['expires'])
                if datetime.now() > expires_date:
                    return False, f"License has expired on {expires_date.strftime('%Y-%m-%d')}.", None
            
            # Check machine binding (optional - can be disabled for flexibility)
            if 'machine_id' in license_data and license_data.get('machine_bound', False):
                current_machine_id = self._get_machine_id()
                if license_data['machine_id'] != current_machine_id:
                    return False, "License is bound to a different machine.", None
            
            # License is valid
            return True, "License is valid.", license_data
            
        except Exception as e:
            return False, f"Error validating license: {str(e)}", None
    
    def _decode_license(self, license_key):
        """
        Decode a license key from base64 format
        
        Format: base64(json_data).base64(signature)
        """
        try:
            # Split license key into data and signature
            parts = license_key.split('.')
            if len(parts) != 2:
                return None
            
            # Decode data
            data_b64 = parts[0]
            signature_b64 = parts[1]
            
            data_json = base64.urlsafe_b64decode(data_b64 + '==')
            license_data = json.loads(data_json)
            
            # Store signature for verification
            license_data['_signature'] = base64.urlsafe_b64decode(signature_b64 + '==')
            
            return license_data
        except Exception as e:
            print(f"Error decoding license: {e}")
            return None
    
    def _verify_signature(self, license_data):
        """Verify the RSA signature of the license data"""
        if not self.public_key:
            return False
        
        try:
            # Extract signature
            signature = license_data.pop('_signature')
            
            # Recreate the data JSON (without signature)
            data_json = json.dumps(license_data, sort_keys=True).encode()
            
            # Verify signature
            self.public_key.verify(
                signature,
                data_json,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            # Restore signature in data for potential future use
            license_data['_signature'] = signature
            
            return True
        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False
    
    def _load_license_from_file(self):
        """Load license key from file"""
        try:
            if os.path.exists(self.LICENSE_FILE):
                with open(self.LICENSE_FILE, 'r', encoding='utf-8') as f:
                    license_data = json.load(f)
                    return license_data.get('license_key')
        except json.JSONDecodeError as e:
            print(f"Error loading license file: Invalid JSON format - {e}")
            # Try to backup corrupted file and remove it
            try:
                backup_file = f"{self.LICENSE_FILE}.corrupted"
                if os.path.exists(self.LICENSE_FILE):
                    import shutil
                    shutil.copy2(self.LICENSE_FILE, backup_file)
                    os.remove(self.LICENSE_FILE)
                    print(f"Corrupted license file backed up to {backup_file} and removed.")
            except Exception as backup_error:
                print(f"Error backing up corrupted license file: {backup_error}")
        except Exception as e:
            print(f"Error loading license file: {e}")
        return None
    
    def save_license(self, license_key):
        """
        Save license key to file
        
        Args:
            license_key: License key string to save
            
        Returns:
            bool: True if saved successfully
        """
        try:
            # Validate before saving
            is_valid, message, license_data = self.validate_license(license_key)
            if not is_valid:
                return False, message
            
            # Save to file
            # Remove _signature from license_data before saving (it's bytes and can't be JSON serialized)
            # We don't need to store it since we can always verify from the license key
            license_data_clean = {k: v for k, v in license_data.items() if k != '_signature'}
            
            license_info = {
                'license_key': license_key,
                'saved_at': datetime.now().isoformat(),
                'license_data': license_data_clean
            }
            
            # Write to temporary file first, then rename (atomic operation)
            temp_file = f"{self.LICENSE_FILE}.tmp"
            try:
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(license_info, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk
                
                # Atomic rename (works on Windows too)
                if os.path.exists(self.LICENSE_FILE):
                    os.replace(temp_file, self.LICENSE_FILE)
                else:
                    os.rename(temp_file, self.LICENSE_FILE)
                
                return True, "License saved successfully."
            except Exception as write_error:
                # Clean up temp file if it exists
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
                raise write_error
        except Exception as e:
            return False, f"Error saving license: {str(e)}"
    
    def get_license_info(self):
        """Get information about the current license"""
        license_key = self._load_license_from_file()
        if not license_key:
            return None
        
        is_valid, message, license_data = self.validate_license(license_key)
        if not is_valid:
            return None
        
        return {
            'valid': True,
            'message': message,
            'data': license_data
        }
    
    def get_machine_id(self):
        """
        Get the current machine ID (public method)
        
        Returns:
            str: Machine ID string
        """
        return self._get_machine_id()


# Global instance
_license_manager = None

def get_license_manager():
    """Get the global license manager instance"""
    global _license_manager
    if _license_manager is None:
        _license_manager = LicenseManager()
    return _license_manager
