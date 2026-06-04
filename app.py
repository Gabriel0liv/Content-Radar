import os
import json

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.storage import (
    fetch_top_videos,
    fetch_top_videos_balanced,
    init_ai_analysis_table,
    init_db,
)

load_dotenv()

USE_POSTGRES = os.getenv("USE_POSTGRES", "false").strip().lower() in {"1", "true", "yes", "sim", "on"}
DB_PATH = os.getenv("DATABASE_PATH", "data/database.sqlite")

st.set_page_config(
    page_title="Dark Content Radar",
    page_icon="📊",
    layout="wide",
)

st.title("Dark Content Radar")
st.caption("Portal de inteligência de conteúdo para encontrar oportunidades originais a partir do YouTube Shorts.")

if USE_POSTGRES:
    # -------------------------------------------------------------
    # POSTGRESQL DASHBOARD (n8n Integration)
    # -------------------------------------------------------------
    from src.postgres_storage import (
        fetch_content_items,
        fetch_content_summary,
        init_postgres_schema_if_needed,
        update_content_status
    )
    
    # Ensure schema exists on startup
    init_postgres_schema_if_needed()
    
    st.subheader("Modo Postgres (Integração n8n)")
    
    try:
        # Load summary stats for metrics
        stats = fetch_content_summary()
        
        # Load all content items to perform interactive filtering in pandas
        items = fetch_content_items(limit=2000)
        df_pg = pd.DataFrame(items)
    except Exception as e:
        st.error(f"Erro ao conectar ou ler dados do PostgreSQL: {e}")
        st.info("Verifique se o container Postgres está rodando (`docker compose up -d`) e se as variáveis de ambiente no `.env` estão corretas.")
        st.stop()
        
    if df_pg.empty:
        st.warning("Nenhum item encontrado no banco Postgres. O banco está conectado, mas a tabela content_items está vazia.")
        
        # Still render metrics with zeros
        col1, col2, col3, col4, col5 = st.columns(5)
        col1.metric("Total de itens", 0)
        col2.metric("Itens novos", 0)
        col3.metric("Fontes ativas", 0)
        col4.metric("Maior score", 0.0)
        col5.metric("Maior views", 0)
        st.stop()

    # Pre-parse dates for filtering
    df_pg["published_at"] = pd.to_datetime(df_pg["published_at"], errors="coerce")
    df_pg["collected_at"] = pd.to_datetime(df_pg["collected_at"], errors="coerce")
    df_pg["last_seen_at"] = pd.to_datetime(df_pg["last_seen_at"], errors="coerce")

    # Render filters in Sidebar
    with st.sidebar:
        st.header("Filtros Postgres")
        
        # Filter 1: source
        sources_list = ["Todos"] + sorted(df_pg["source"].dropna().unique().tolist())
        selected_source = st.selectbox("Fonte", sources_list, index=0)
        
        # Filter 2: content_type
        content_types_list = ["Todos"] + sorted(df_pg["content_type"].dropna().unique().tolist())
        selected_content_type = st.selectbox("Content Type", content_types_list, index=0)
        
        # Filter 3: status
        expected_statuses = ["Todos", "new", "reviewed", "selected", "rejected", "produced", "archived"]
        db_statuses = df_pg["status"].dropna().unique().tolist()
        for s in db_statuses:
            if s not in expected_statuses:
                expected_statuses.append(s)
        selected_status = st.selectbox("Status", expected_statuses, index=0)
        
        # Filter 4: topic_seed
        topic_seeds_list = ["Todos"] + sorted(df_pg["topic_seed"].dropna().unique().tolist())
        selected_topic_seed = st.selectbox("Topic Seed", topic_seeds_list, index=0)
        
        # Filter 5: score mínimo
        min_score_pg = st.slider(
            "Score mínimo",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=0.5,
        )
        
        # Filter 6: views mínimo
        min_views_pg = st.number_input(
            "Views mínimo",
            min_value=0,
            value=0,
            step=1000,
        )
        
        # Filter 7: data de publicação
        min_pub_date = df_pg["published_at"].min()
        max_pub_date = df_pg["published_at"].max()
        
        if pd.notna(min_pub_date) and pd.notna(max_pub_date):
            # date_input can fail if dates are invalid or min/max date are same, handle safety
            min_d = min_pub_date.date()
            max_d = max_pub_date.date()
            if min_d == max_d:
                date_range = st.date_input(
                    "Data de publicação",
                    value=min_d,
                    min_value=min_d,
                    max_value=max_d
                )
                # wrap in tuple to unify type
                if not isinstance(date_range, tuple):
                    date_range = (date_range, date_range)
            else:
                date_range = st.date_input(
                    "Data de publicação",
                    value=(min_d, max_d),
                    min_value=min_d,
                    max_value=max_d
                )
        else:
            date_range = None

    # Apply filters in Pandas
    filtered_pg = df_pg.copy()
    
    if selected_source != "Todos":
        filtered_pg = filtered_pg[filtered_pg["source"] == selected_source]
        
    if selected_content_type != "Todos":
        filtered_pg = filtered_pg[filtered_pg["content_type"] == selected_content_type]
        
    if selected_status != "Todos":
        filtered_pg = filtered_pg[filtered_pg["status"] == selected_status]
        
    if selected_topic_seed != "Todos":
        filtered_pg = filtered_pg[filtered_pg["topic_seed"] == selected_topic_seed]
        
    filtered_pg = filtered_pg[filtered_pg["score"] >= min_score_pg]
    filtered_pg = filtered_pg[filtered_pg["views"] >= min_views_pg]
    
    if date_range and len(date_range) == 2:
        start_date, end_date = date_range
        filtered_pg = filtered_pg[
            (filtered_pg["published_at"].dt.date >= start_date) &
            (filtered_pg["published_at"].dt.date <= end_date)
        ]

    # Metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    col1.metric("Total de itens", stats.get("total_items", 0))
    col2.metric("Itens novos", stats.get("new_items", 0))
    
    sources_breakdown = stats.get("items_by_source", {})
    breakdown_text = "\n".join([f"- {src}: {count}" for src, count in sources_breakdown.items()])
    col3.metric("Fontes ativas", len(sources_breakdown), help=f"Itens por Fonte:\n{breakdown_text}")
    
    col4.metric("Maior score", f"{stats.get('max_score', 0.0):.2f}")
    col5.metric("Maior views", f"{stats.get('max_views', 0):,}")

    st.subheader("Itens Coletados pelo n8n")
    st.caption("Filtros aplicados à tabela de resultados persistidos no banco de dados local.")

    if filtered_pg.empty:
        st.warning("Nenhum item corresponde aos filtros selecionados.")
    else:
        show_cols = [
            "id",
            "score",
            "status",
            "source",
            "content_type",
            "topic_seed",
            "title",
            "url",
            "views",
            "likes",
            "comments",
            "published_at",
            "discovery_query",
            "language",
            "country_code"
        ]
        
        available_cols = [c for c in show_cols if c in filtered_pg.columns]
        
        st.dataframe(
            filtered_pg[available_cols].sort_values(by=["score", "published_at"], ascending=[False, False]),
            use_container_width=True,
            hide_index=True
        )
        
    st.markdown("---")
    st.subheader("Ações rápidas (Desenvolvimento)")
    st.caption("Código preparado para alteração de status via painel.")
    with st.expander("Ver código de exemplo para atualização de status"):
        st.code("""
# Exemplo de fluxo para atualizar o status de um item
if st.button("Marcar item 1 como 'reviewed'"):
    update_content_status(1, "reviewed")
    st.success("Status atualizado com sucesso!")
        """, language="python")

else:
    # -------------------------------------------------------------
    # ORIGINAL SQLITE DASHBOARD
    # -------------------------------------------------------------
    from src.storage import (
        fetch_top_videos,
        fetch_top_videos_balanced,
        init_ai_analysis_table,
        init_db,
    )
    
    ENV_VIRAL_ONLY = os.getenv("VIRAL_ONLY", "true").strip().lower() in {"1", "true", "yes", "sim", "on"}
    ENV_VIRAL_ACCEPTANCE_MODE = os.getenv("VIRAL_ACCEPTANCE_MODE", "or").strip().lower()
    if ENV_VIRAL_ACCEPTANCE_MODE not in {"or", "and"}:
        ENV_VIRAL_ACCEPTANCE_MODE = "or"
    ENV_MIN_TOTAL_VIEWS = int(os.getenv("MIN_TOTAL_VIEWS", "1000000"))
    ENV_MIN_VIEWS_PER_DAY = int(os.getenv("MIN_VIEWS_PER_DAY", "100000"))
    ENV_VIRAL_STRICT_MODE = os.getenv("VIRAL_STRICT_MODE", "false").strip().lower() in {"1", "true", "yes", "sim", "on"}

    init_db(DB_PATH)
    init_ai_analysis_table(DB_PATH)
    
    with st.sidebar:
        st.header("Filtros")
    
        ranking_mode = st.selectbox(
            "Modo de ranking",
            options=["Geral", "Balanceado por nicho"],
            index=0,
        )
    
    if ranking_mode == "Balanceado por nicho":
        videos = fetch_top_videos_balanced(DB_PATH, per_niche=5, total_limit=500)
    else:
        videos = fetch_top_videos(DB_PATH, limit=500)
    
    if not videos:
        st.warning("Ainda não existem vídeos no banco. Rode primeiro: python main.py")
        st.stop()
    
    df = pd.DataFrame(videos)
    has_niche_relevance_score = "niche_relevance_score" in df.columns
    
    with st.sidebar:
        niches = sorted(df["niche"].dropna().unique().tolist())
        selected_niches = st.multiselect(
            "Nichos",
            options=niches,
            default=niches,
        )
    
        min_score = st.slider(
            "Score mínimo",
            min_value=0,
            max_value=100,
            value=40,
        )
    
        min_views_per_day = st.number_input(
            "Views/dia mínimo",
            min_value=0,
            value=0,
            step=1000,
        )
    
        viral_only_filter = st.checkbox(
            "Viral only",
            value=ENV_VIRAL_ONLY,
        )
    
        min_total_views = st.number_input(
            "Total views mínimo",
            min_value=0,
            value=ENV_MIN_TOTAL_VIEWS,
            step=100000,
        )
    
        min_viral_views_per_day = st.number_input(
            "Viral views/dia mínimo",
            min_value=0,
            value=ENV_MIN_VIEWS_PER_DAY,
            step=10000,
        )
    
        viral_tier_filter = st.selectbox(
            "Viral tier",
            options=["all", "rising", "viral", "mega_viral"],
            index=0,
        )
    
        show_rising = st.checkbox(
            "Mostrar rising",
            value=not ENV_VIRAL_STRICT_MODE,
        )
    
        discovery_source_options = (
            ["all"]
            + sorted(
                [
                    value
                    for value in df.get("discovery_source", pd.Series(dtype=str)).dropna().unique().tolist()
                ]
            )
        )
        discovery_source_filter = st.selectbox(
            "Discovery source",
            options=discovery_source_options,
            index=0,
        )
    
        candidate_niche_options = (
            ["all"]
            + sorted(
                [
                    value
                    for value in df.get("candidate_niche", pd.Series(dtype=str)).dropna().unique().tolist()
                ]
            )
        )
        candidate_niche_filter = st.selectbox(
            "Candidate niche",
            options=candidate_niche_options,
            index=0,
        )
    
        discovery_query_options = sorted(
            [
                value
                for value in df.get("discovery_query", pd.Series(dtype=str)).dropna().unique().tolist()
            ]
        )
        selected_discovery_queries = st.multiselect(
            "Discovery query",
            options=discovery_query_options,
            default=[],
        )
    
        source_language_filter = st.selectbox(
            "Source language",
            options=["all", "pt", "en", "es", "unknown"],
            index=0,
        )
    
        recommended_action_options = (
            ["all"]
            + sorted(
                [
                    value
                    for value in df.get("recommended_action", pd.Series(dtype=str)).dropna().unique().tolist()
                ]
            )
        )
        recommended_action_filter = st.selectbox(
            "Recommended action",
            options=recommended_action_options,
            index=0,
        )
    
        content_category_options = (
            ["all"]
            + sorted(
                [
                    value
                    for value in df.get("content_category", pd.Series(dtype=str)).dropna().unique().tolist()
                ]
            )
        )
        content_category_filter = st.selectbox(
            "Content category",
            options=content_category_options,
            index=0,
        )
    
        adaptation_type_options = (
            ["all"]
            + sorted(
                [
                    value
                    for value in df.get("adaptation_type", pd.Series(dtype=str)).dropna().unique().tolist()
                ]
            )
        )
        adaptation_type_filter = st.selectbox(
            "Adaptation type",
            options=adaptation_type_options,
            index=0,
        )
    
        min_localization_potential = st.slider(
            "Localization potential mínimo",
            min_value=0,
            max_value=100,
            value=0,
        )
    
        min_creator_fit = st.slider(
            "Creator fit mínimo",
            min_value=0,
            max_value=100,
            value=0,
        )
    
        max_ip_risk = st.selectbox(
            "IP risk máximo",
            options=["high", "medium", "low"],
            index=0,
        )
    
        only_good_references = st.checkbox(
            "Mostrar apenas boas referências",
            value=False,
        )
        only_foreign_adaptable = st.checkbox(
            "Mostrar apenas oportunidades adaptáveis da gringa",
            value=False,
        )
        st.caption("Esse filtro só funciona depois de rodar `python analyze.py`.")
    
    filtered = df[
        (df["niche"].isin(selected_niches))
        & (df["opportunity_score"] >= min_score)
        & (df["views_per_day"] >= min_views_per_day)
    ].copy()
    
    if viral_only_filter and {"views", "views_per_day"}.issubset(filtered.columns):
        total_condition = filtered["views"].fillna(0) >= min_total_views
        velocity_condition = filtered["views_per_day"].fillna(0) >= min_viral_views_per_day
        if ENV_VIRAL_ACCEPTANCE_MODE == "and":
            filtered = filtered[total_condition & velocity_condition].copy()
        else:
            filtered = filtered[total_condition | velocity_condition].copy()
    elif "views" in filtered.columns and "views_per_day" in filtered.columns:
        filtered = filtered[
            (filtered["views"].fillna(0) >= min_total_views)
            & (filtered["views_per_day"].fillna(0) >= min_viral_views_per_day)
        ].copy()
    
    if viral_only_filter and "is_viral_candidate" in filtered.columns:
        filtered = filtered[filtered["is_viral_candidate"] == 1].copy()
    
    if not show_rising and "viral_tier" in filtered.columns:
        filtered = filtered[filtered["viral_tier"] != "rising"].copy()
    
    if "viral_tier" in filtered.columns and viral_tier_filter != "all":
        filtered = filtered[filtered["viral_tier"] == viral_tier_filter].copy()
    
    if "discovery_source" in filtered.columns and discovery_source_filter != "all":
        filtered = filtered[filtered["discovery_source"] == discovery_source_filter].copy()
    
    if "candidate_niche" in filtered.columns and candidate_niche_filter != "all":
        filtered = filtered[filtered["candidate_niche"] == candidate_niche_filter].copy()
    
    if "discovery_query" in filtered.columns and selected_discovery_queries:
        filtered = filtered[filtered["discovery_query"].isin(selected_discovery_queries)].copy()
    
    risk_order = {"low": 1, "medium": 2, "high": 3}
    
    if "source_language" in filtered.columns and source_language_filter != "all":
        filtered = filtered[filtered["source_language"] == source_language_filter].copy()
    
    if "recommended_action" in filtered.columns and recommended_action_filter != "all":
        filtered = filtered[filtered["recommended_action"] == recommended_action_filter].copy()
    
    if "content_category" in filtered.columns and content_category_filter != "all":
        filtered = filtered[filtered["content_category"] == content_category_filter].copy()
    
    if "adaptation_type" in filtered.columns and adaptation_type_filter != "all":
        filtered = filtered[filtered["adaptation_type"] == adaptation_type_filter].copy()
    
    if "localization_potential" in filtered.columns:
        filtered = filtered[filtered["localization_potential"].fillna(0) >= min_localization_potential].copy()
    
    if "creator_fit_score" in filtered.columns:
        filtered = filtered[filtered["creator_fit_score"].fillna(0) >= min_creator_fit].copy()
    
    if "ip_risk" in filtered.columns:
        filtered = filtered[
            filtered["ip_risk"].fillna("high").map(risk_order).fillna(3) <= risk_order[max_ip_risk]
        ].copy()
    
    has_ai_analyses = (
        "is_good_reference" in df.columns
        and df["is_good_reference"].notna().sum() > 0
    )
    
    if only_good_references:
        if has_ai_analyses:
            filtered = filtered[filtered["is_good_reference"] == 1].copy()
    
    if only_foreign_adaptable and has_ai_analyses:
        filtered = filtered[
            filtered["source_language"].isin(["en", "es"])
            & filtered["recommended_action"].isin(["use_as_reference", "adapt_with_research"])
            & (filtered["localization_potential"].fillna(0) >= 70)
        ].copy()
    
    
    def _format_ideas(value):
        if not value:
            return ""
    
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            return str(value)
    
        if not isinstance(parsed, list):
            return str(value)
    
        return " | ".join(str(item) for item in parsed if str(item).strip())
    
    
    if "original_angle_ideas" in filtered.columns:
        filtered["original_angle_ideas"] = filtered["original_angle_ideas"].apply(
            _format_ideas
        )
    
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("Vídeos no banco", len(df))
    col2.metric("Vídeos filtrados", len(filtered))
    col3.metric(
        "Maior score",
        round(filtered["opportunity_score"].max(), 2) if not filtered.empty else 0,
    )
    col4.metric(
        "Maior views/dia", int(filtered["views_per_day"].max()) if not filtered.empty else 0
    )
    
    if filtered.empty:
        st.warning(
            "Nenhum vídeo passou nos filtros atuais. Reduza MIN_TOTAL_VIEWS, MIN_VIEWS_PER_DAY ou ative rising."
        )
    
    st.subheader("Top sinais virais do YouTube")
    st.caption(
        "Esses sinais podem vir de keywords de nicho, buscas amplas ou vídeos populares do YouTube. A classificação editorial final vem depois da análise IA."
    )
    
    show_columns = [
        "opportunity_score",
        "viral_tier",
        "is_viral_candidate",
        "discovery_source",
        "discovery_query",
        "candidate_niche",
        "niche",
        "title",
        "channel_title",
        "views",
        "views_per_day",
        "comments",
        "comment_rate",
        "duration_seconds",
        "url",
    ]
    
    if has_niche_relevance_score:
        show_columns.insert(4, "niche_relevance_score")
    
    viral_tier_order = {"mega_viral": 4, "viral": 3, "rising": 2, "weak": 1}
    signals_df = filtered.copy()
    if "viral_tier" in signals_df.columns:
        signals_df["_viral_tier_rank"] = signals_df["viral_tier"].map(viral_tier_order).fillna(0)
    else:
        signals_df["_viral_tier_rank"] = 0
    
    st.dataframe(
        signals_df[show_columns + ["_viral_tier_rank"]].sort_values(
            by=["_viral_tier_rank", "views_per_day", "views", "opportunity_score"],
            ascending=False,
        )[show_columns],
        use_container_width=True,
        hide_index=True,
    )
    
    st.subheader("Top oportunidades para produção")
    st.caption(
        "Use esta tabela para decidir o que produzir. Ela considera análise IA, adaptação, risco, perfil editorial e potencial de produção."
    )
    
    ai_columns = [
        "source_language",
        "target_market",
        "content_category",
        "content_format",
        "adaptation_type",
        "is_good_reference",
        "detected_language",
        "real_niche",
        "hook_type",
        "dark_channel_fit",
        "creator_fit_score",
        "localization_potential",
        "cultural_fit_br",
        "evergreen_score",
        "production_priority_score",
        "production_difficulty",
        "copyright_risk",
        "reused_content_risk",
        "ip_risk",
        "source_dependency_risk",
        "brand_or_product_risk",
        "controversy_level",
        "recommended_action",
        "opportunity_reason",
        "original_angle_ideas",
    ]
    
    available_ai_columns = [column for column in ai_columns if column in filtered.columns]
    
    if only_good_references and not has_ai_analyses:
        st.warning(
            "O filtro 'Mostrar apenas boas referências' exige análises IA salvas. Rode `python analyze.py` primeiro."
        )
    elif not has_ai_analyses:
        st.info("Ainda não existem análises IA salvas. Rode: python analyze.py")
    else:
        ai_df = filtered[
            [
                "title",
                "channel_title",
                "niche",
                "opportunity_score",
                "url",
                *available_ai_columns,
            ]
        ].copy()
        st.dataframe(
            ai_df.sort_values(
                by=[
                    "production_priority_score",
                    "localization_potential",
                    "creator_fit_score",
                    "opportunity_score",
                ],
                ascending=[False, False, False, False],
            ),
            use_container_width=True,
            hide_index=True,
        )
    
    st.subheader("Resumo por nicho")
    
    if filtered.empty:
        summary = pd.DataFrame(
            columns=[
                "niche",
                "videos",
                "avg_score",
                "max_score",
                "avg_views_per_day",
                "max_views_per_day",
            ]
        )
    else:
        summary = (
            filtered.groupby("niche")
            .agg(
                videos=("video_id", "count"),
                avg_score=("opportunity_score", "mean"),
                max_score=("opportunity_score", "max"),
                avg_views_per_day=("views_per_day", "mean"),
                max_views_per_day=("views_per_day", "max"),
            )
            .sort_values(by="max_score", ascending=False)
            .reset_index()
        )
    
    st.dataframe(summary, use_container_width=True, hide_index=True)
