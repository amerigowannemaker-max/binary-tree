#!/usr/bin/env python3
"""Encrypt the new signing key to an owner-held RSA public key before export."""
import base64
import io
import json
import os
import zipfile
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

root = Path(__file__).resolve().parents[1]
keyfile = Path(os.environ['STUDY_SIGN_KEYSTORE'])
password = os.environ['STUDY_SIGN_PASSWORD']
buffer = io.BytesIO()
with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as z:
    z.write(keyfile, 'tianjin-ds-2027-release.jks')
    z.writestr('keystore-password.txt', password + '\n')
    z.writestr('README.txt', 'Private Android signing backup. Alias: study-release.\nKeep private. Reuse this key for future updates.\n')
public = serialization.load_pem_public_key((root / 'ci/signing-backup-public.pem').read_bytes())
key = AESGCM.generate_key(bit_length=256)
nonce = os.urandom(12)
aad = b'tianjin-ds-2027-release-signing-backup-v1'
ciphertext = AESGCM(key).encrypt(nonce, buffer.getvalue(), aad)
wrapped = public.encrypt(key, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
encode = lambda value: base64.b64encode(value).decode('ascii')
envelope = {'format':'rsa-oaep-sha256+a256gcm-v1','wrapped_key':encode(wrapped),
            'nonce':encode(nonce),'aad':encode(aad),'ciphertext':encode(ciphertext)}
out = root / 'verification/signing-backup.encrypted.json'
out.write_text(json.dumps(envelope, indent=2) + '\n')
print('Exported encrypted signing backup; no plaintext private key or password is uploaded')
