"""生成 ed25519 SSH 密钥对(OpenSSH 格式)。"""
from __future__ import annotations

import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

SSH_DIR = Path(os.environ["USERPROFILE"]) / ".ssh"
KEY_PATH = SSH_DIR / "id_ed25519"
PUB_PATH = SSH_DIR / "id_ed25519.pub"
COMMENT = "hanfaxiang@browserflow.local"


def main() -> None:
    SSH_DIR.mkdir(parents=True, exist_ok=True)

    if KEY_PATH.exists():
        print(f"[SKIP] {KEY_PATH} 已存在,未覆盖。")
    else:
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        # 私钥:OpenSSH 格式,无密码
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.OpenSSH,
            encryption_algorithm=serialization.NoEncryption(),
        )
        KEY_PATH.write_bytes(private_bytes)
        os.chmod(KEY_PATH, 0o600)

        # 公钥:OpenSSH 单行格式
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH,
        )
        PUB_PATH.write_text(f"{public_bytes.decode()} {COMMENT}\n")

    print(f"私钥: {KEY_PATH}")
    print(f"公钥: {PUB_PATH}")
    print("--- 公钥内容(整行复制到 GitHub Settings → SSH keys)---")
    print(PUB_PATH.read_text().strip())


if __name__ == "__main__":
    main()