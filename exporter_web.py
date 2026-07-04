# Injecte les données pré-agrégées dans index.html (dashboard HTML/CSS/JS
# autonome, sans Streamlit). À relancer si les CSV de ../data/ changent :
#   python3 exporter_web.py
#
# Le JSON est écrit entre les marqueurs « DONNEES » du fichier index.html.
# Les agrégats mensuels portent (n, moyenne, écart-type) par groupe
# région × denrée × mois, ce qui permet de recalculer côté JS des moyennes
# et écarts-types exacts sur n'importe quel sous-ensemble filtré.

import json
import re

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

DATA = "../data"
NOMS_CLUSTERS = {0: "Ouest / urbain", 1: "Sud / vallée du fleuve",
                 2: "Bassin arachidier"}


def indice_mois(annee, mois):
    """Index de mois compact : 0 = janvier 2000."""
    return int((annee - 2000) * 12 + mois - 1)


def profil_regions(df):
    """Les 5 indicateurs régionaux de l'ACP (mêmes définitions que le rapport)."""
    df = df.copy()
    df["temps"] = df["annee"] + (df["mois"] - 1) / 12
    mensuel = df.groupby(["region", "temps"])["prix_fcfa"].mean().reset_index()
    saison = df.groupby(["region", "saison"])["prix_fcfa"].mean().unstack()
    X = pd.DataFrame({
        "prix_moyen": df.groupby("region")["prix_fcfa"].mean(),
        "prix_volatilite": df.groupby("region")["prix_fcfa"].std(),
        "saisonnalite_prix": (df.groupby(["region", "mois"])["prix_fcfa"].mean()
                                .groupby("region").std()),
        "tendance_prix": mensuel.groupby("region").apply(
            lambda g: np.polyfit(g["temps"], g["prix_fcfa"], 1)[0],
            include_groups=False),
        "ecart_saison": saison["Hivernage"] - saison["Saison sèche"],
    })
    F = PCA(n_components=2).fit_transform(StandardScaler().fit_transform(X))
    X["PC1"], X["PC2"] = F[:, 0], F[:, 1]
    return X.reset_index()


df = pd.read_csv(f"{DATA}/dataset_pretraite_senegal.csv", parse_dates=["date"])
historique = pd.read_csv(f"{DATA}/app_series_historiques.csv",
                         parse_dates=["date"])
previsions = pd.read_csv(f"{DATA}/app_previsions.csv", parse_dates=["date"])
recap = pd.read_csv(f"{DATA}/previsions_recap.csv")
clusters = pd.read_csv(f"{DATA}/clusters_regions.csv")

denrees = sorted(df["nom_denree"].unique())
regions = sorted(df["region"].unique())

# ── Agrégat mensuel région × denrée × mois : [iRegion, iDenree, t, n, m, s] ──
g = (df.groupby(["region", "nom_denree", "annee", "mois"])["prix_fcfa"]
       .agg(n="count", m="mean", s="std").reset_index())
mensuel = [[regions.index(r.region), denrees.index(r.nom_denree),
            indice_mois(r.annee, r.mois), int(r.n),
            round(r.m, 2), round(0 if pd.isna(r.s) else r.s, 2)]
           for r in g.itertuples()]

# ── Heatmap région × denrée (moyenne brute, comme le pivot du rapport) ──
pivot = df.pivot_table(values="prix_fcfa", index="region",
                       columns="nom_denree", aggfunc="mean")
heatmap = [[None if pd.isna(pivot.loc[r, d]) else round(pivot.loc[r, d])
            for d in denrees] for r in regions]

# ── Profils régionaux (ACP + clusters) ──
profils = profil_regions(df).merge(clusters, on="region")
profils_json = [{
    "region": p.region, "cluster": NOMS_CLUSTERS[p.cluster],
    "prixMoyen": round(p.prix_moyen, 1),
    "volatilite": round(p.prix_volatilite, 1),
    "saisonnalite": round(p.saisonnalite_prix, 1),
    "tendance": round(p.tendance_prix, 2),
    "pc1": round(p.PC1, 3), "pc2": round(p.PC2, 3),
} for p in profils.itertuples()]

# ── Séries nationales : 48 derniers mois + 12 mois de prévision par denrée ──
hist_json, prev_json, recap_json = {}, {}, {}
for d in denrees:
    h = historique[historique["denree"] == d].tail(48)
    hist_json[d] = [[indice_mois(x.date.year, x.date.month),
                     round(x.prix, 1)] for x in h.itertuples()]
    p = previsions[previsions["denree"] == d]
    prev_json[d] = [[indice_mois(x.date.year, x.date.month),
                     round(x.prix_prevu, 1), round(x.ic_bas, 1),
                     round(x.ic_haut, 1)] for x in p.itertuples()]
    i = recap.set_index("Denrée").loc[d]
    recap_json[d] = {"sarima": i["SARIMA"], "mape": round(i["MAPE_%"], 1)}

donnees = {"denrees": denrees, "regions": regions, "anneeMin": 2000,
           "anneeMax": 2017, "mensuel": mensuel, "heatmap": heatmap,
           "profils": profils_json, "historique": hist_json,
           "previsions": prev_json, "recap": recap_json}

with open("index.html", encoding="utf-8") as f:
    page = f.read()
bloc = ("// --- DONNEES (générées par exporter_web.py) ---\n"
        f"const DONNEES = {json.dumps(donnees, ensure_ascii=False)};\n"
        "// --- FIN DONNEES ---")
page, n = re.subn(r"// --- DONNEES.*?// --- FIN DONNEES ---", bloc, page,
                  flags=re.S)
assert n == 1, "Marqueurs DONNEES introuvables dans index.html"
with open("index.html", "w", encoding="utf-8") as f:
    f.write(page)
print(f"index.html mis à jour : {len(mensuel)} groupes mensuels, "
      f"{len(bloc) / 1e3:.0f} Ko de données.")
