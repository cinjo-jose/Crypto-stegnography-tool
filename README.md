# Crypto Steganography Tool

A Python-based tool for securely embedding sensitive data within digital images using AES-256 encryption and RSA public-key cryptography.

## Overview

This tool combines three security techniques to hide data undetectably within images:

- **AES-256 Encryption** — Encrypts data with a 256-bit symmetric key
- **RSA Public-Key Cryptography** — Encrypts the session key with 4096-bit RSA
- **Seeded LSB Steganography** — Scatters hidden bits randomly across image pixels
- **Zlib Compression** — Reduces data size by ~30% before encryption

## Features

- ✓ Two-tier encryption (AES-256 + RSA-4096) for maximum security
- ✓ Seeded random LSB distribution resistant to steganalysis
- ✓ Automatic filename preservation during extraction
- ✓ Cross-platform support (Windows, Linux, macOS)
- ✓ Supports PNG, BMP, TIFF, and TGA image formats
- ✓ Lossless data recovery

## Installation

### Requirements
- Python 3.7 or higher

### Setup

1. Clone or download the repository:
```bash
git clone https://github.com/cinjo-jose/crypto-steganography-tool.git
cd crypto-steganography-tool
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Generate RSA Keys

First, generate a public/private key pair:

```bash
python generate_keys.py
```

When prompted, enter a strong passphrase to protect your private key. This creates:
- `myprivatekey.pem` — Your encrypted RSA private key (keep this safe!)
- `mypublickey.pem` — Your RSA public key (share this to let others hide data for you)

### 2. Hide Data in an Image

Embed a secret file inside an image:

```bash
python secret_pixel.py hide image.png secret.txt mypublickey.pem output.png
```

**Arguments:**
- `image.png` — Host image (PNG, BMP, TIFF, or TGA)
- `secret.txt` — File to hide
- `mypublickey.pem` — Public key for encryption
- `output.png` — Output image with embedded data

### 3. Extract Data from an Image

Recover the hidden file:

```bash
python secret_pixel.py extract output.png myprivatekey.pem secret.txt
```

**Arguments:**
- `output.png` — Image containing hidden data
- `myprivatekey.pem` — Private key for decryption
- `secret.txt` (optional) — Output filename. If omitted, the original filename is used.

When prompted, enter the passphrase you used when generating the private key.

## How It Works

### Hiding Process

1. **Read the secret file** and compress it with zlib
2. **Generate a random session key** (256-bit)
3. **Encrypt the compressed data** using AES-256-CBC
4. **Encrypt the session key** using RSA-4096-OAEP
5. **Combine**: filename + encrypted_session_key + salt + IV + encrypted_data
6. **Distribute across pixels** using a seeded random number generator
7. **Save the stego-image** in the requested format

### Extraction Process

1. **Extract bits** from image pixels using the same seed
2. **Recover the metadata** (filename, keys, IV, ciphertext)
3. **Decrypt the session key** using RSA-4096
4. **Decrypt the data** using AES-256-CBC
5. **Decompress** using zlib
6. **Save the original file** with its original filename

## Security Considerations

- **Image Size:** The host image must be at least 3× larger than the secret file
- **Image Format:** Use lossless formats (PNG, TIFF) for best results. Avoid lossy formats (JPG)
- **Image Content:** Images with high color variation hide data more effectively
- **Key Protection:** Keep your private key passphrase strong and secure
- **Seeded Randomness:** The distribution of hidden bits is predictable only with the seed (image dimensions)

## Example

```bash
# Generate keys (one-time setup)
python generate_keys.py
# Enter passphrase: MySecurePassphrase123!

# Hide a secret document
python secret_pixel.py hide landscape.png confidential.pdf mypublickey.pem landscape_hidden.png

# Extract the secret (requires private key passphrase)
python secret_pixel.py extract landscape_hidden.png myprivatekey.pem confidential.pdf
# Enter private key passphrase: MySecurePassphrase123!
```

## Supported Image Formats

| Format | Quality | Best For |
|--------|---------|----------|
| PNG    | Lossless| Recommended |
| BMP    | Lossless| Simple, raw pixels |
| TIFF   | Lossless| Professional use |
| TGA    | Lossless| High-detail images |

**Note:** Avoid JPEG and other lossy formats — compression will destroy hidden data.

## Technical Details

### Encryption

- **Symmetric:** AES-256 in CBC mode with PKCS7 padding
- **Key Derivation:** PBKDF2-HMAC-SHA256 (200,000 iterations)
- **Asymmetric:** RSA-4096 with OAEP padding and SHA-256
- **IV:** 128-bit random, unique per encryption

### Steganography

- **Method:** Least Significant Bit (LSB) matching
- **Distribution:** Seeded random (derived from image width + height)
- **Seed:** Non-secret; allows only the original image to extract correctly
- **Capacity:** Up to 1/3 of image size in bytes

## Limitations

- Hidden data is limited to approximately 1/3 of the image file size
- Extracting from a modified image (crop, resize, filter) will fail
- Image metadata is not preserved during the embedding process
- The tool requires the original host image dimensions to extract data

## Troubleshooting

**"Image is not large enough to hide the file"**
- Use a larger host image (at least 3× the size of your secret file)

**"Incorrect passphrase" during extraction**
- Double-check your private key passphrase
- Ensure you're using the correct private key for the data

**"Unsupported image format"**
- Convert your image to PNG, BMP, TIFF, or TGA using an image editor

## License

This project is released under the GNU General Public License v3.0.

See the [LICENSE](LICENSE) file for details, or visit [GNU GPL v3.0](https://www.gnu.org/licenses/gpl-3.0.en.html).

## Contributing

Contributions, bug reports, and feature requests are welcome! Feel free to:
- Open an issue for bugs or suggestions
- Submit a pull request with improvements
- Help improve documentation

---

**Built with:** Python 3, cryptography library, PIL/Pillow, NumPy
