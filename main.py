import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from src.scorer import score_videos
from src.storage import (
    fetch_top_videos_balanced,
    init_ai_analysis_table,
    init_db,
    upsert_videos,
)
from src.youtube_collector import search_recent_short_videos

KEYWORDS_BY_NICHE = {
    "História sombria": [
        "história sombria",
        "curiosidades históricas",
        "fatos históricos",
        "mistérios da história",
        "história bizarra",
    ],
    "Psicologia": [
        "fatos psicológicos",
        "psicologia humana",
        "comportamento humano",
        "curiosidades sobre o cérebro",
        "mente humana",
    ],
    "Mistérios reais": [
        "mistérios reais",
        "casos inexplicáveis",
        "fatos bizarros",
        "histórias reais assustadoras",
        "casos estranhos reais",
    ],
    "IA e tecnologia": [
        "ferramentas de ia",
        "inteligência artificial",
        "chatgpt produtividade",
        "apps de ia",
        "automação com ia",
    ],
    "Finanças básicas": [
        "erros financeiros",
        "finanças pessoais",
        "economizar dinheiro",
        "hábitos financeiros",
        "educação financeira",
    ],
}


def main():
    load_dotenv()

    api_key = os.getenv("YOUTUBE_API_KEY")
    db_path = os.getenv("DATABASE_PATH", "data/database.sqlite")
    days_back = int(os.getenv("DAYS_BACK", "7"))
    region_code = os.getenv("REGION_CODE", "BR")
    max_results = int(os.getenv("MAX_RESULTS_PER_KEYWORD", "25"))

    if not api_key:
        raise RuntimeError("Falta YOUTUBE_API_KEY no arquivo .env")

    init_db(db_path)
    init_ai_analysis_table(db_path)


    published_after = datetime.now(timezone.utc) - timedelta(days=days_back)

    all_videos = []

    for niche, keywords in KEYWORDS_BY_NICHE.items():
        print(f"\n=== Nicho: {niche} ===")

        for keyword in keywords:
            print(f"Buscando: {keyword}")

            try:
                videos = search_recent_short_videos(
                    api_key=api_key,
                    keyword=keyword,
                    niche=niche,
                    published_after=published_after,
                    region_code=region_code,
                    max_results=max_results,
                )

                scored = score_videos(videos)
                all_videos.extend(scored)

                print(
                    f"Coletados: {len(videos)} | Aprovados após filtros: {len(scored)}"
                )

            except Exception as error:
                print(f"Erro ao buscar '{keyword}': {error}")

    if all_videos:
        collected_at = datetime.now(timezone.utc).isoformat()

        for video in all_videos:
            video["collected_at"] = collected_at

        upsert_videos(db_path, all_videos)

    print("\n\nTOP VÍDEOS ENCONTRADOS — RANKING BALANCEADO")
    print("===========================================")

    top_videos = fetch_top_videos_balanced(db_path, per_niche=5, total_limit=20)

    for index, video in enumerate(top_videos, start=1):
        print(
            f"{index}. [{video['niche']}] "
            f"{video['opportunity_score']} pts | "
            f"{int(video['views_per_day'])} views/dia | "
            f"{video['title']} | "
            f"{video['url']}"
        )


if __name__ == "__main__":
    main()
