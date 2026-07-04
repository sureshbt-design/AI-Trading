import pandas as pd


def rank_candidates(results, score_column="Score"):
    """
    Sort candidates by score and assign a rank.
    """

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame(results)

    df = df.sort_values(
        by=score_column,
        ascending=False
    ).reset_index(drop=True)

    df["Rank"] = range(1, len(df) + 1)

    cols = ["Rank"] + [c for c in df.columns if c != "Rank"]

    return df[cols]


def top_candidates(results, top_n=10):
    ranked = rank_candidates(results)
    return ranked.head(top_n)
    