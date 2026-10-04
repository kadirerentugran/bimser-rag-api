import re
import unicodedata


def slugify(text: str) -> str:
    """
    Herhangi bir metni URL-safe, ASCII dosya adına çevirir.
    Türkçe karakterleri dönüştürür, boşlukları tire yapar.
    Örnek: "Başlangıç ve Kurulum" → "baslangic-ve-kurulum"
    """
    tr_map = str.maketrans(
        "ğüşıöçĞÜŞİÖÇ",
        "gusiocGUSIOC"
    )
    text = text.translate(tr_map)

    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    text = text.lower()

    text = re.sub(r"[^a-z0-9]+", "-", text)

    text = text.strip("-")

    return text
