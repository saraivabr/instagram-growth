#!/usr/bin/env python3
"""
Inicializa credenciais de uma conta Instagram de forma segura.

Credenciais são isoladas em ~/.config/instagram-growth/<username>/
nunca entrando no repositório.

Fluxo:
1. Valida access_token na API
2. Busca username da conta
3. Cria diretório ~/.config/instagram-growth/<username>/
4. Salva access_token (criptografado se possível)
5. Retorna config pra usar em outras ferramentas
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Optional
from getpass import getpass

# Se rodar via CLI, importa nosso cliente
try:
    from ig import InstagramAPIClient, InstagramAPIError
except ImportError:
    # Ou do diretório scripts/
    sys.path.insert(0, str(Path(__file__).parent))
    from ig import InstagramAPIClient, InstagramAPIError


def secure_input(prompt: str, sensitive: bool = False) -> str:
    """Captura input do usuário (sensível = sem echo)."""
    if sensitive:
        return getpass(prompt)
    return input(prompt)


def validate_token(access_token: str) -> Optional[Dict]:
    """
    Valida se o token é válido pra Instagram.
    Retorna info da conta se válido, None se inválido.
    """
    try:
        # Primeiro, descobrir o business_account_id usando o token
        # A gente faz um request simples pra /me pra ter certeza que o token funciona
        import requests

        url = "https://graph.instagram.com/v18.0/me"
        params = {"fields": "id,username", "access_token": access_token}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            print(f"❌ Erro no token: {data['error'].get('message', 'Unknown error')}")
            return None

        return data

    except Exception as e:
        print(f"❌ Erro ao validar token: {str(e)}")
        return None


def create_config_dir(username: str) -> Path:
    """Cria e retorna diretório de config pra conta."""
    config_dir = Path("~/.config/instagram-growth").expanduser() / username
    config_dir.mkdir(parents=True, exist_ok=True)
    # Permissões restritivas
    os.chmod(config_dir, 0o700)
    return config_dir


def save_credentials(
    config_dir: Path,
    access_token: str,
    business_account_id: str,
    username: str,
) -> None:
    """Salva credentials no config dir de forma segura."""
    credentials_file = config_dir / "credentials.json"

    credentials = {
        "access_token": access_token,
        "business_account_id": business_account_id,
        "username": username,
        "created_at": datetime.now().isoformat(),
    }

    credentials_file.write_text(json.dumps(credentials, indent=2))
    os.chmod(credentials_file, 0o600)  # Apenas leitura do owner

    print(f"✅ Credenciais salvas em {credentials_file}")


def init_account(access_token: str) -> Dict:
    """
    Fluxo completo de inicialização de uma conta.

    Returns:
        {
            "username": "@seu_username",
            "business_account_id": "ig_...",
            "config_dir": "~/.config/instagram-growth/seu_username",
            "status": "success" | "error"
        }
    """
    print("\n📸 Inicializando conta Instagram...\n")

    # 1. Validar token
    print("🔐 Validando access token...")
    account_info = validate_token(access_token)

    if not account_info:
        return {"status": "error", "message": "Token inválido"}

    # 2. Buscar informações da conta
    print(f"✅ Token válido!")
    username = account_info.get("username", "unknown")
    business_account_id = account_info.get("id")

    print(f"   Conta: @{username} (ID: {business_account_id})")

    # 3. Criar config dir
    print(f"\n📁 Criando diretório de configuração...")
    config_dir = create_config_dir(username)
    print(f"   {config_dir}")

    # 4. Salvar credentials
    print(f"\n🔒 Salvando credenciais...")
    save_credentials(config_dir, access_token, business_account_id, username)

    # 5. Testar conexão
    print(f"\n🧪 Testando conexão com API...")
    try:
        client = InstagramAPIClient(access_token, business_account_id, str(config_dir))
        full_info = client.get_account_info()
        print(f"   ✅ Conexão OK")
        print(f"   Nome: {full_info.get('name')}")
        print(f"   Seguidores: {full_info.get('followers_count', 'N/A')}")
        print(f"   Posts: {full_info.get('media_count', 'N/A')}")
    except Exception as e:
        print(f"   ⚠️  Aviso ao testar: {str(e)}")

    return {
        "status": "success",
        "username": username,
        "business_account_id": business_account_id,
        "config_dir": str(config_dir),
    }


def load_credentials(username: str) -> Optional[Dict]:
    """Carrega credentials salvos pra uma conta."""
    config_dir = Path("~/.config/instagram-growth").expanduser() / username
    credentials_file = config_dir / "credentials.json"

    if not credentials_file.exists():
        return None

    try:
        return json.loads(credentials_file.read_text())
    except Exception:
        return None


def main():
    """CLI pra inicializar uma conta."""
    if len(sys.argv) > 1:
        # Access token passado via argumento
        access_token = sys.argv[1]
    else:
        # Perguntar
        print("Cole seu access token do Meta Apps (ou Ctrl+C pra cancelar):")
        access_token = secure_input("Access token: ", sensitive=True)

    if not access_token:
        print("❌ Token necessário")
        sys.exit(1)

    result = init_account(access_token)

    if result["status"] == "success":
        print(f"\n✨ Conta inicializada com sucesso!")
        print(f"\n📋 Próximos passos:")
        print(f"   1. Execute: /instagram-growth:start")
        print(f"   2. Escolha a conta: @{result['username']}")
    else:
        print(f"\n❌ Erro: {result.get('message')}")
        sys.exit(1)


if __name__ == "__main__":
    from datetime import datetime
    main()
