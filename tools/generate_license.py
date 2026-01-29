"""
License Key Generator Tool
Generates signed license keys for Kathana Helper

Usage:
    python tools/generate_license.py
    
This tool generates a private/public key pair and creates signed license keys.
Keep the private key SECRET - it should never be included in the distributed application.
"""
import os
import sys
import json
import base64
import argparse
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend


def generate_key_pair():
    """Generate a new RSA key pair"""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    return private_key


def save_key_pair(private_key, private_key_file="private_key.pem", public_key_file="public_key.pem"):
    """Save private and public keys to files"""
    # Save private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    with open(private_key_file, 'wb') as f:
        f.write(private_pem)
    print(f"[OK] Private key saved to: {private_key_file}")
    print(f"  [WARNING] KEEP THIS FILE SECRET - Never distribute it!")
    
    # Save public key
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with open(public_key_file, 'wb') as f:
        f.write(public_pem)
    print(f"[OK] Public key saved to: {public_key_file}")
    print(f"  -> This key should be embedded in the application")
    
    return public_key


def load_private_key(private_key_file="private_key.pem"):
    """Load private key from file"""
    try:
        with open(private_key_file, 'rb') as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
        return private_key
    except FileNotFoundError:
        print(f"Error: Private key file '{private_key_file}' not found.")
        print("Generate a new key pair first or specify the correct path.")
        return None
    except Exception as e:
        print(f"Error loading private key: {e}")
        return None


def generate_license_key(private_key, user_name="User", days_valid=365, machine_id=None, machine_bound=False):
    """
    Generate a signed license key
    
    Args:
        private_key: RSA private key for signing
        user_name: Name of the license holder
        days_valid: Number of days the license is valid
        machine_id: Optional machine ID to bind license to
        machine_bound: Whether to bind license to specific machine
        
    Returns:
        str: Base64-encoded license key
    """
    # Create license data
    license_data = {
        'user_name': user_name,
        'issued': datetime.now().isoformat(),
        'expires': (datetime.now() + timedelta(days=days_valid)).isoformat(),
        'version': '1.0'
    }
    
    if machine_id:
        license_data['machine_id'] = machine_id
        license_data['machine_bound'] = machine_bound
    
    # Create signature
    data_json = json.dumps(license_data, sort_keys=True).encode()
    signature = private_key.sign(
        data_json,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    
    # Encode license key: base64(data).base64(signature)
    data_b64 = base64.urlsafe_b64encode(data_json).decode().rstrip('=')
    signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')
    
    license_key = f"{data_b64}.{signature_b64}"
    
    return license_key, license_data


def main():
    parser = argparse.ArgumentParser(description='Generate signed license keys for Kathana Helper')
    parser.add_argument('--generate-keys', action='store_true', help='Generate a new key pair')
    parser.add_argument('--private-key', default='private_key.pem', help='Path to private key file')
    parser.add_argument('--user', default='User', help='License holder name')
    parser.add_argument('--days', type=int, default=365, help='Number of days license is valid')
    parser.add_argument('--machine-id', help='Machine ID to bind license to (optional)')
    parser.add_argument('--machine-bound', action='store_true', help='Bind license to specific machine')
    parser.add_argument('--output', help='Output file for license key (optional)')
    
    args = parser.parse_args()
    
    # Generate key pair if requested
    if args.generate_keys:
        print("Generating new RSA key pair...")
        private_key = generate_key_pair()
        public_key = save_key_pair(private_key)
        print("\n[OK] Key pair generated successfully!")
        print("\nNext steps:")
        print("1. Embed the public key in license_manager.py")
        print("2. Keep the private key secure and use it to generate license keys")
        print("3. Never distribute the private key!")
        return
    
    # Load private key
    private_key = load_private_key(args.private_key)
    if not private_key:
        print("\nTo generate a new key pair, run:")
        print("  python tools/generate_license.py --generate-keys")
        return
    
    # Generate license key
    print(f"Generating license key for: {args.user}")
    print(f"Valid for: {args.days} days")
    
    license_key, license_data = generate_license_key(
        private_key,
        user_name=args.user,
        days_valid=args.days,
        machine_id=args.machine_id,
        machine_bound=args.machine_bound
    )
    
    # Display license info
    print("\n" + "="*60)
    print("LICENSE KEY GENERATED")
    print("="*60)
    print(f"User: {license_data['user_name']}")
    print(f"Issued: {license_data['issued']}")
    print(f"Expires: {license_data['expires']}")
    if 'machine_id' in license_data:
        print(f"Machine ID: {license_data['machine_id']}")
        print(f"Machine Bound: {license_data.get('machine_bound', False)}")
    print("\nLicense Key:")
    print("-"*60)
    print(license_key)
    print("-"*60)
    
    # Save to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            f.write(license_key)
        print(f"\n[OK] License key saved to: {args.output}")
    
    print("\n[OK] License key generated successfully!")
    print("\nCopy the license key above and provide it to the user.")


if __name__ == "__main__":
    main()
