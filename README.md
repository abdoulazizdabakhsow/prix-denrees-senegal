# Application — dashboard interactif

Dashboard du projet (partie 9 du rapport) : exploration des prix,
comparaison des régions (ACP + clusters) et prévision SARIMA à 1–12 mois.
Design inspiré d'une maquette « EcoSync » (cartes arrondies, carte insight
en dégradé, carte vert foncé, badges et barres de progression).

Deux implémentations sont fournies :

## 1. Version HTML/CSS/JS autonome (`index.html`) — recommandée

Un seul fichier, **sans serveur ni dépendance** : ouvrir `index.html` dans
un navigateur (double-clic). Les graphiques (courbes, barres, heatmap, ACP,
prévision avec intervalle de confiance) sont dessinés en SVG/JS pur, avec
infobulles et filtres interactifs. Les données sont pré-agrégées et
embarquées dans la page par :

```bash
python3 exporter_web.py   # à relancer seulement si les CSV de ../data changent
```

Les agrégats mensuels portent (effectif, moyenne, écart-type) par
région × denrée × mois : le JS recalcule des moyennes et écarts-types
exacts (identiques à pandas) sur n'importe quel sous-ensemble filtré.

## 2. Version Streamlit (`app.py`)

```bash
streamlit run app.py
```

Le navigateur s'ouvre sur http://localhost:8501 (3 onglets : Explorer,
Comparer les régions, Prévoir). Thème dans `.streamlit/config.toml`,
composants HTML/CSS injectés via `st.markdown(unsafe_allow_html=True)`.

Dépendances : `streamlit`, `plotly`, `pandas`, `scikit-learn`
(`pip install streamlit plotly pandas scikit-learn`).

## Régénérer les prévisions (optionnel)

Les prévisions lues par le dashboard sont pré-calculées dans
`../data/app_previsions.csv` et `../data/app_series_historiques.csv`.
Pour les recalculer (nécessite `statsmodels`) :

```bash
python3 exporter_previsions.py
```

Les ordres SARIMA utilisés sont ceux sélectionnés par AIC dans le notebook

`../serie_temporelle/Series_temporelles_toutes_denrees.ipynb`.
