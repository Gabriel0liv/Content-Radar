import json
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

from src.ai_analyzer import analyze_video_opportunity
from src.storage import (
    fetch_videos_for_ai_analysis,
    init_ai_analysis_table,
    init_db,
    save_ai_analysis,
)


def calculate_production_priority_score(video: dict, analysis: dict) -> float:
    language_bonus = {
        "pt": 10,
        "unknown": 3,
    }.get(analysis.get("detected_language"), 0)
    risk_penalty = {
        "low": 0,
        "medium": 10,
        "high": 25,
    }.get(analysis.get("copyright_risk"), 10) + {
        "low": 0,
        "medium": 10,
        "high": 25,
    }.get(analysis.get("reused_content_risk"), 10)
    difficulty_penalty = {
        "low": 0,
        "medium": 8,
        "high": 18,
    }.get(analysis.get("production_difficulty"), 8)

    score = (
        float(video.get("opportunity_score", 0)) * 0.45
        + float(analysis.get("dark_channel_fit", 0)) * 0.35
        + language_bonus
        - risk_penalty
        - difficulty_penalty
    )

    if not analysis.get("is_good_reference", False):
        score = min(score, 40)

    return round(max(0, min(100, score)), 2)


def main() -> None:
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    db_path = os.getenv("DATABASE_PATH", "data/database.sqlite")
    analysis_limit = int(os.getenv("AI_ANALYSIS_LIMIT", "20"))

    if not api_key:
        raise RuntimeError("Falta GEMINI_API_KEY no arquivo .env")

    init_db(db_path)
    init_ai_analysis_table(db_path)

    videos = fetch_videos_for_ai_analysis(db_path, limit=analysis_limit)
    if not videos:
        print("Nenhum vídeo novo encontrado para análise IA.")
        return

    for video in videos:
        try:
            analysis = analyze_video_opportunity(api_key=api_key, model=model, video=video)
            production_priority_score = calculate_production_priority_score(
                video=video,
                analysis=analysis,
            )
            record = {
                "video_id": video["video_id"],
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
                "model": model,
                "is_good_reference": analysis["is_good_reference"],
                "detected_language": analysis["detected_language"],
                "real_niche": analysis["real_niche"],
                "content_type": analysis["content_type"],
                "hook_type": analysis["hook_type"],
                "retention_pattern": analysis["retention_pattern"],
                "dark_channel_fit": analysis["dark_channel_fit"],
                "production_difficulty": analysis["production_difficulty"],
                "copyright_risk": analysis["copyright_risk"],
                "reused_content_risk": analysis["reused_content_risk"],
                "fact_check_needed": analysis["fact_check_needed"],
                "opportunity_reason": analysis["opportunity_reason"],
                "original_angle_ideas": json.dumps(analysis["original_angle_ideas"], ensure_ascii=False),
                "production_priority_score": production_priority_score,
                "raw_json": analysis["raw_json"],
            }
            save_ai_analysis(db_path, record)

            print(f"[OK] {video['title']}")
            print(f"good_reference: {'sim' if analysis['is_good_reference'] else 'não'}")
            print(f"language: {analysis['detected_language']}")
            print(f"dark_fit: {analysis['dark_channel_fit']}")
            print(f"risk: {analysis['copyright_risk']}")
            print(f"production_priority_score: {production_priority_score}")
            print(f"reason: {analysis['opportunity_reason']}")
            print()
        except Exception as error:
            print(f"[ERRO] {video['title']}")
            print(f"reason: {error}")
            print()


if __name__ == "__main__":
    main()
