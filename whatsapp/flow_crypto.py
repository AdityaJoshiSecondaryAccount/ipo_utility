import json
import logging
from base64 import b64decode, b64encode

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.padding import MGF1, OAEP
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import load_pem_private_key

logger = logging.getLogger(__name__)


class FlowDecryptionError(Exception):
    """Raised when incoming Flow payload cannot be decrypted."""
    pass


def load_private_key(private_key_pem: str or bytes, passphrase: str = None):
    """Load RSA private key from PEM bytes or string."""
    if isinstance(private_key_pem, str):
        private_key_pem = private_key_pem.encode("utf-8")

    password_bytes = passphrase.encode("utf-8") if passphrase else None
    return load_pem_private_key(private_key_pem, password=password_bytes)


def decrypt_request(
    encrypted_flow_data_b64: str,
    encrypted_aes_key_b64: str,
    initial_vector_b64: str,
    private_key_pem: str or bytes,
    passphrase: str = None,
) -> tuple[dict, bytes, bytes]:
    """
    Decrypts an incoming WhatsApp Flow request according to Meta's data_api_version 3.0 specification.
    
    Returns:
        (decrypted_dict, aes_key, iv)
    """
    try:
        flow_data = b64decode(encrypted_flow_data_b64)
        encrypted_aes_key = b64decode(encrypted_aes_key_b64)
        iv = b64decode(initial_vector_b64)

        # 1. Decrypt AES Key using RSA-OAEP SHA-256 / MGF1(SHA-256)
        private_key = load_private_key(private_key_pem, passphrase)
        aes_key = private_key.decrypt(
            encrypted_aes_key,
            OAEP(
                mgf=MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )

        # 2. Decrypt Flow Data using AES-128-GCM (last 16 bytes is authentication tag)
        tag_length = 16
        if len(flow_data) < tag_length:
            raise FlowDecryptionError("Flow data payload too short to contain auth tag.")

        encrypted_body = flow_data[:-tag_length]
        auth_tag = flow_data[-tag_length:]

        decryptor = Cipher(
            algorithms.AES(aes_key),
            modes.GCM(iv, auth_tag),
        ).decryptor()

        decrypted_bytes = decryptor.update(encrypted_body) + decryptor.finalize()
        decrypted_data = json.loads(decrypted_bytes.decode("utf-8"))

        return decrypted_data, aes_key, iv

    except Exception as e:
        logger.error(f"Failed to decrypt WhatsApp Flow request: {e}", exc_info=True)
        raise FlowDecryptionError(str(e)) from e


def encrypt_response(response_dict: dict, aes_key: bytes, iv: bytes) -> str:
    """
    Encrypts response payload according to Meta WhatsApp Flows 3.0 specification:
    - Inverts all bits of the initialization vector (XOR with 0xFF).
    - Encrypts JSON payload with AES-GCM using the flipped IV.
    - Appends 16-byte authentication tag to ciphertext.
    - Returns Base64-encoded plain text string.
    """
    try:
        # 1. Flip the initialization vector (XOR each byte with 0xFF)
        flipped_iv = bytearray(b ^ 0xFF for b in iv)

        # 2. Encrypt with AES-GCM
        encryptor = Cipher(
            algorithms.AES(aes_key),
            modes.GCM(flipped_iv),
        ).encryptor()

        json_bytes = json.dumps(response_dict, separators=(",", ":")).encode("utf-8")
        ciphertext = encryptor.update(json_bytes) + encryptor.finalize()

        # 3. Append tag and return Base64 string
        encrypted_payload = ciphertext + encryptor.tag
        return b64encode(encrypted_payload).decode("utf-8")

    except Exception as e:
        logger.error(f"Failed to encrypt WhatsApp Flow response: {e}", exc_info=True)
        raise
