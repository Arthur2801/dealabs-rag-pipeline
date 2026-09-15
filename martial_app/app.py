"""Interface Streamlit de recherche sémantique des bons plans Dealabs."""

import streamlit as st

from i18n import LANGUAGES, TEXT
from rag_logic import get_deals_rag, get_llm_answer

st.set_page_config(
    page_title="Dealabs | Recherche sémantique",
    layout="wide",
)


def show_deal(deal: dict, labels: dict) -> None:
    """Afficher uniquement les champs réellement produits par le pipeline."""
    with st.container(border=True):
        st.subheader(deal.get("title") or "Dealabs")
        price = deal.get("price")
        if isinstance(price, (int, float)):
            st.write(f"**{price:.2f} €**")
        category = deal.get("group_display_summary")
        if category:
            st.caption(f"{labels['category']} : {category}")
        score = deal.get("score")
        if isinstance(score, (int, float)):
            st.caption(f"{labels['score']} : {score:.2f}")
        if deal.get("text"):
            with st.expander(labels["details"]):
                st.write(deal["text"])
        if deal.get("url"):
            st.link_button(labels["open"], deal["url"])


def main() -> None:
    language_name = st.sidebar.selectbox("Langue / Language / Idioma", LANGUAGES)
    language = LANGUAGES[language_name]
    labels = TEXT[language]

    st.title(labels["title"])
    st.caption(labels["subtitle"])

    with st.form("deal_search"):
        query = st.text_input(labels["query"], placeholder=labels["placeholder"])
        max_price = st.slider(labels["budget"], 0, 10000, 1200)
        submitted = st.form_submit_button(labels["search"])

    if submitted and query.strip():
        query = query.strip()
        with st.spinner(labels["loading"]):
            try:
                results = get_deals_rag(query, max_price)
            except Exception:
                st.session_state.pop("search", None)
                st.error(labels["search_error"])
                return

            answer = None
            if results:
                try:
                    answer = get_llm_answer(query, results, language)
                except Exception:
                    st.warning(labels["summary_error"])
            st.session_state["search"] = {
                "results": results,
                "answer": answer,
                "language": language,
            }

    search = st.session_state.get("search")
    if not search:
        return

    results = search["results"]
    if not results:
        st.info(labels["no_results"])
        return

    if search["answer"] and search["language"] == language:
        st.subheader(labels["summary"])
        st.write(search["answer"])

    st.subheader(f"{labels['results']} · {len(results)}")
    for deal in results:
        show_deal(deal, labels)


if __name__ == "__main__":
    main()
