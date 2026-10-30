import random

# Function to check if a number is prime
def is_prime(n):
    if n <= 1:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

# Function to calculate GCD
def gcd(a, b):
    while b:
        a, b = b, a % b
    return a

# Function to compute modular inverse using brute force
def modinv(a, m):
    for x in range(1, m):
        if (a * x) % m == 1:
            return x
    return None

# RSA Key Generation with fixed primes to ensure fixed modulus
def generate_keys():
    p = 131  # Fixed prime number
    q = 137  # Fixed prime number

    n = p * q              # Modulus (fixed)
    phi = (p - 1) * (q - 1)  # Euler's totient

    e = 65537  # Commonly used public exponent
    # If 65537 isn't valid, choose a random one
    if gcd(e, phi) != 1:
        e = random.randint(2, phi - 1)
        while gcd(e, phi) != 1:
            e = random.randint(2, phi - 1)

    d = modinv(e, phi)  # Private exponent

    print(f"Public exponent (e): {e}")
    print(f"Private exponent (d): {d}")
    print(f"Modulus (n): {n}")

    return e, d, n

# Encrypt message using public key (e, n)
def encrypt(message, e, n):
    cipher = [pow(ord(char), e, n) for char in message]
    return cipher

# Decrypt cipher using private key (d, n)
def decrypt(cipher, d, n):
    decrypted_text = ''.join([chr(pow(char, d, n)) for char in cipher])
    return decrypted_text

# --- MAIN PROGRAM ---
if __name__ == "__main__":
    e, d, n = generate_keys()

    # msg = "00416D63"
    # msg = "2CEDEA20"
    # msg = "0091A6DB"
    # msg = "C0520E64"
    # msg = "0012CD0C"
    # msg = "0020D9E9"
    # msg = "0029794F"
    # msg = "0049BEEC"
    msg = "A68AEDF7"
    print("Original Message:", msg)

    encrypted = encrypt(msg, e, n)
    print("Encrypted:", encrypted)

    decrypted = decrypt(encrypted, d, n)
    print("Decrypted:", decrypted)
