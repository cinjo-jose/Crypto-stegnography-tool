from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from getpass import getpass


def generate_rsa_keys():
    """Generate 4096-bit RSA public and private keys."""
    print("Generating 4096-bit RSA key pair...")
    
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096,
        backend=default_backend()
    )

    password = getpass("RSA Private Key Passphrase: ").encode('utf-8')

    encryption_algorithm = serialization.BestAvailableEncryption(password)

    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption_algorithm
    )

    with open("myprivatekey.pem", "wb") as f:
        f.write(pem_private)

    public_key = private_key.public_key()

    pem_public = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    with open("mypublickey.pem", "wb") as f:
        f.write(pem_public)

    print("✓ myprivatekey.pem created (encrypted with your passphrase)")
    print("✓ mypublickey.pem created (can be shared safely)")


if __name__ == '__main__':
    generate_rsa_keys()
