import argparse
import sys
import os
import random
from PIL import Image
import numpy as np
from cryptography.hazmat.primitives.padding import PKCS7
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import zlib
from getpass import getpass


def encrypt_data(data, public_key):
    """Encrypt data using AES-256 and RSA."""
    session_key = os.urandom(32)
    salt = os.urandom(16)
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200000,
        backend=default_backend()
    )
    key = kdf.derive(session_key)
    
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    padder = PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(data) + padder.finalize()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    
    encrypted_session_key = public_key.encrypt(
        session_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    
    return encrypted_session_key, salt, iv, encrypted_data


def decrypt_data(encrypted_session_key, salt, iv, encrypted_data, private_key):
    """Decrypt data using RSA and AES-256."""
    session_key = private_key.decrypt(
        encrypted_session_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=200000,
        backend=default_backend()
    )
    key = kdf.derive(session_key)
    
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
    unpadder = PKCS7(algorithms.AES.block_size).unpadder()
    decrypted_data = unpadder.update(decrypted_padded_data) + unpadder.finalize()
    
    return decrypted_data


def compute_seed_from_image_dimensions(image_path):
    """Generate seed from image dimensions."""
    with Image.open(image_path) as img:
        width, height = img.size
    return width + height


def hide_file_in_image(image_path, file_to_hide, output_image_path, public_key_path):
    """Hide a file inside an image."""
    with open(public_key_path, 'rb') as key_file:
        public_key = serialization.load_pem_public_key(
            key_file.read(),
            backend=default_backend()
        )

    seed = compute_seed_from_image_dimensions(image_path)
    prng = random.Random(seed)

    img = Image.open(image_path)

    if img.mode not in ['RGB', 'RGBA', 'P', 'L']:
        raise ValueError("Image mode must be RGB, RGBA, P (palette), or L (grayscale).")

    if img.mode in ['P', 'L']:
        img = img.convert('RGB')

    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    host_format = img.format
    if host_format is None:
        file_extension = os.path.splitext(image_path)[1].lower()
        extension_to_format = {
            '.tga': 'TGA',
            '.png': 'PNG',
            '.bmp': 'BMP',
            '.tif': 'TIFF',
            '.tiff': 'TIFF',
        }
        host_format = extension_to_format.get(file_extension)

    supported_formats = {'TGA', 'TIFF', 'BMP', 'PNG'}
    if host_format not in supported_formats:
        raise ValueError(f"Unsupported image format: {host_format}")

    pixels = np.array(img)

    with open(file_to_hide, 'rb') as f:
        file_bytes = f.read()

    compressed_data = zlib.compress(file_bytes)
    encrypted_session_key, salt, iv, encrypted_data = encrypt_data(compressed_data, public_key)

    filename = os.path.basename(file_to_hide).encode()
    filename_size = len(filename)

    data_to_encode = (filename_size.to_bytes(4, 'big') + filename +
                      encrypted_session_key + salt + iv + encrypted_data)

    file_size = len(data_to_encode)
    num_pixels_required = file_size * 8
    if num_pixels_required > pixels.size // 4:
        raise ValueError("Image is not large enough to hide the file.")

    pixel_indices = list(range(pixels.size // 4))
    prng.shuffle(pixel_indices)

    for i in range(64):
        idx = pixel_indices[i]
        bit = (file_size >> (63 - i)) & 0x1
        if (pixels[idx // pixels.shape[1], idx % pixels.shape[1], 0] & 0x1) != bit:
            pixels[idx // pixels.shape[1], idx % pixels.shape[1], 0] ^= 0x1

    for i, byte in enumerate(data_to_encode):
        for bit in range(8):
            idx = pixel_indices[64 + i * 8 + bit]
            if (pixels[idx // pixels.shape[1], idx % pixels.shape[1], 0] & 0x1) != ((byte >> (7 - bit)) & 0x1):
                pixels[idx // pixels.shape[1], idx % pixels.shape[1], 0] ^= 0x1

    if os.path.exists(output_image_path):
        overwrite = input(f"File '{output_image_path}' exists. Overwrite? (y/n): ").lower()
        if overwrite != 'y':
            print("Operation cancelled.")
            return

    new_img = Image.fromarray(pixels, 'RGBA')

    if host_format == 'PNG':
        new_img.save(output_image_path, format='PNG', optimize=True)
    elif host_format == 'BMP':
        new_img.save(output_image_path, format='BMP', optimize=True)
    elif host_format == 'TGA':
        new_img.save(output_image_path, format='TGA', optimize=True)
    elif host_format == 'TIFF':
        new_img.save(output_image_path, format='TIFF', optimize=True)

    print(f"✓ File '{file_to_hide}' hidden in '{output_image_path}'.")


def extract_file_from_image(image_path, output_file_path, private_key_path):
    """Extract a hidden file from an image."""
    passphrase = getpass("Enter private key passphrase: ")
    with open(private_key_path, 'rb') as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=passphrase.encode(),
            backend=default_backend()
        )

    encrypted_session_key_size = private_key.key_size // 8

    seed = compute_seed_from_image_dimensions(image_path)
    prng = random.Random(seed)

    img = Image.open(image_path)
    if img.mode not in ['RGB', 'RGBA']:
        raise ValueError("Image must be in RGB or RGBA format.")

    if img.mode != 'RGBA':
        img = img.convert('RGBA')

    pixels = np.array(img)

    pixel_indices = list(range(pixels.size // 4))
    prng.shuffle(pixel_indices)

    file_size = 0
    for i in range(64):
        idx = pixel_indices[i]
        file_size = (file_size << 1) | (pixels[idx // pixels.shape[1], idx % pixels.shape[1], 0] & 0x1)

    extracted_bytes = []
    for i in range(file_size):
        byte = 0
        for bit in range(8):
            idx = pixel_indices[64 + i * 8 + bit]
            byte = (byte << 1) | (pixels[idx // pixels.shape[1], idx % pixels.shape[1], 0] & 0x1)
        extracted_bytes.append(byte)

    data_to_decode = bytes(extracted_bytes)

    filename_size = int.from_bytes(data_to_decode[:4], 'big')
    filename = data_to_decode[4:4 + filename_size].decode()

    offset = 4 + filename_size
    encrypted_session_key = data_to_decode[offset:offset + encrypted_session_key_size]
    salt = data_to_decode[offset + encrypted_session_key_size:offset + encrypted_session_key_size + 16]
    iv = data_to_decode[offset + encrypted_session_key_size + 16:offset + encrypted_session_key_size + 32]
    encrypted_data = data_to_decode[offset + encrypted_session_key_size + 32:]

    decrypted_data = decrypt_data(encrypted_session_key, salt, iv, encrypted_data, private_key)
    decompressed_data = zlib.decompress(decrypted_data)

    if not output_file_path:
        output_file_path = os.path.join(os.getcwd(), filename)

    if os.path.exists(output_file_path):
        overwrite = input(f"File '{output_file_path}' exists. Overwrite? (y/n): ").lower()
        if overwrite != 'y':
            print("Operation cancelled.")
            return

    with open(output_file_path, 'wb') as f:
        f.write(decompressed_data)

    print(f"✓ File extracted to '{output_file_path}'.")


def main():
    parser = argparse.ArgumentParser(
        description='Crypto Steganography Tool - Hide secrets in images',
        epilog="Examples:\n"
               "  Hide:    python secret_pixel.py hide image.png secret.txt key.pem output.png\n"
               "  Extract: python secret_pixel.py extract output.png key.pem secret.txt",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest='command')

    hide_parser = subparsers.add_parser('hide', help='Hide a file inside an image')
    hide_parser.add_argument('host', type=str, help='Host image path')
    hide_parser.add_argument('secret', type=str, help='Secret file to hide')
    hide_parser.add_argument('pubkey', type=str, help='Public key file')
    hide_parser.add_argument('output', type=str, help='Output image path')

    extract_parser = subparsers.add_parser('extract', help='Extract a hidden file from an image')
    extract_parser.add_argument('carrier', type=str, help='Image with hidden data')
    extract_parser.add_argument('privkey', type=str, help='Private key file')
    extract_parser.add_argument('extracted', nargs='?', type=str, default=None, help='Output file (optional)')

    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()

    if args.command == 'hide':
        hide_file_in_image(args.host, args.secret, args.output, args.pubkey)
    elif args.command == 'extract':
        output_file_path = args.extracted if args.extracted else None
        extract_file_from_image(args.carrier, output_file_path, args.privkey)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
