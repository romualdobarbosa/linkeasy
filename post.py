import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import requests

load_dotenv()

TOKEN_FILE = ".token.json"
QUEUE_DIR = Path("posting/queue")
PUBLISHED_DIR = Path("posting/published")
PERSON_ID = os.getenv("LINKEDIN_PERSON_ID")


def load_token():
    with open(TOKEN_FILE) as f:
        return json.load(f)["access_token"]


def parse_post(file: Path):
    content = file.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return None, content.strip()

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, content.strip()

    frontmatter = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            frontmatter[key.strip()] = value.strip()

    body = parts[2].strip()
    return frontmatter, body


def is_due(scheduled_at: str) -> bool:
    try:
        scheduled = datetime.strptime(scheduled_at, "%Y-%m-%d %H:%M")
        return datetime.now() >= scheduled
    except ValueError:
        return False


def upload_image(token: str, image_path: Path) -> str:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "LinkedIn-Version": "202506",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    init_response = requests.post(
        "https://api.linkedin.com/rest/images?action=initializeUpload",
        headers=headers,
        json={"initializeUploadRequest": {"owner": f"urn:li:person:{PERSON_ID}"}},
    )
    init_response.raise_for_status()
    data = init_response.json()["value"]
    upload_url = data["uploadUrl"]
    image_urn = data["image"]

    with open(image_path, "rb") as f:
        upload_response = requests.put(
            upload_url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/octet-stream"},
            data=f,
        )
    upload_response.raise_for_status()

    return image_urn


def find_image(post_file: Path) -> Path | None:
    image_dir = post_file.parent / post_file.stem
    if not image_dir.is_dir():
        return None
    for ext in ("*.png", "*.jpg", "*.jpeg"):
        images = sorted(image_dir.glob(ext))
        if images:
            return images[0]
    return None


def publish(token: str, text: str, image_path: Path | None = None):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "LinkedIn-Version": "202506",
        "X-Restli-Protocol-Version": "2.0.0",
    }
    body = {
        "author": f"urn:li:person:{PERSON_ID}",
        "commentary": text,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    if image_path:
        print(f"Enviando imagem: {image_path.name}")
        image_urn = upload_image(token, image_path)
        body["content"] = {"media": {"id": image_urn}}

    response = requests.post(
        "https://api.linkedin.com/rest/posts",
        headers=headers,
        json=body,
    )
    if not response.ok:
        print(f"Erro {response.status_code}: {response.text}")
    response.raise_for_status()
    return response


def main():
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)

    posts = sorted(QUEUE_DIR.glob("*.md"))
    if not posts:
        print("Nenhum post na fila.")
        return

    token = load_token()
    posted = 0

    for post_file in posts:
        frontmatter, body = parse_post(post_file)

        if frontmatter is None:
            print(f"Ignorando {post_file.name}: sem frontmatter.")
            continue

        if frontmatter.get("status") == "posted":
            continue

        scheduled_at = frontmatter.get("scheduled_at", "")
        if not is_due(scheduled_at):
            print(f"Agendado para {scheduled_at} — ainda nao e a hora.")
            continue

        image_path = find_image(post_file)
        print(f"Postando: {post_file.name}" + (f" + {image_path.name}" if image_path else ""))
        publish(token, body, image_path)

        dest = PUBLISHED_DIR / post_file.name
        shutil.move(str(post_file), str(dest))
        print(f"Publicado e movido para posting/published/")
        posted += 1

    if posted == 0:
        print("Nenhum post para publicar agora.")


if __name__ == "__main__":
    main()
