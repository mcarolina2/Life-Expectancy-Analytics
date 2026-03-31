import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# ══════════════════════════════════════════════════════════════════════════════
#  DADOS
# ══════════════════════════════════════════════════════════════════════════════
df_real = pd.read_csv("dados/idh.csv")

df_fake = pd.read_csv("dados/idh_sintetico.csv")
for col in df_fake.columns:
    if col != "ano_referencia":
        df_fake[col] = df_fake[col].astype(str).str.replace(",", ".", regex=False)
        df_fake[col] = pd.to_numeric(df_fake[col], errors="coerce")
df_fake = df_fake.sort_values("ano_referencia").reset_index(drop=True)

ANO_MIN         = int(df_real["ano_referencia"].min())
ANO_MAX         = int(df_real["ano_referencia"].max())
ANOS_GENERO_MIN = 2002

# ══════════════════════════════════════════════════════════════════════════════
#  TEMA
# ══════════════════════════════════════════════════════════════════════════════
BG     = "#0D1117"
CARD   = "#161B22"
BORDER = "#30363D"
TEXT   = "#E6EDF3"
MUTED  = "#8B949E"
ACCENT = "#58A6FF"
GREEN  = "#3FB950"
PURPLE = "#BC8CFF"
ORANGE = "#FF8C42"
RED    = "#F85149"
FONT   = "Inter, Segoe UI, sans-serif"

LBASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TEXT, family=FONT, size=12),
    margin=dict(l=44, r=20, t=44, b=50),
    xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
    yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER),
    legend=dict(orientation="h", y=-0.22),
)

# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS DE LAYOUT
# ══════════════════════════════════════════════════════════════════════════════
def card(children, extra=None):
    s = {"background": CARD, "border": f"1px solid {BORDER}",
         "borderRadius": "12px", "padding": "20px"}
    if extra:
        s.update(extra)
    return html.Div(children, style=s)

def kpi_box(label, value_id, color=ACCENT):
    return card([
        html.P(label, style={"color": MUTED, "fontSize": "11px", "margin": "0 0 4px",
                              "textTransform": "uppercase", "letterSpacing": "0.4px"}),
        html.H3(id=value_id, children="—",
                style={"color": color, "margin": "0", "fontSize": "24px", "fontWeight": "700"}),
    ], extra={"flex": "1", "minWidth": "130px"})

def _dd(options, value, id_, width="170px"):
    return dcc.Dropdown(
        id=id_, options=options, value=value, clearable=False,
        style={"backgroundColor": BG, "color": TEXT,
               "border": f"1px solid {BORDER}", "borderRadius": "8px",
               "fontSize": "13px", "width": width},
    )

def _chip(label, el):
    return html.Div([
        html.Span(label, style={"color": MUTED, "fontSize": "12px",
                                "marginRight": "8px", "whiteSpace": "nowrap"}),
        el,
    ], style={"display": "flex", "alignItems": "center"})

def range_slider(id_, mn, mx, step=1):
    marks = {y: {"label": str(y), "style": {"color": MUTED, "fontSize": "10px"}}
             for y in range(mn, mx + 1, 5 if (mx - mn) > 10 else 2)}
    return dcc.RangeSlider(
        id=id_, min=mn, max=mx, value=[mn, mx], step=step,
        marks=marks,
        tooltip={"placement": "bottom", "always_visible": True},
        allowCross=False,
    )

def filter_bar(children):
    return card(
        html.Div(children,
                 style={"display": "flex", "alignItems": "center",
                        "gap": "28px", "flexWrap": "wrap"}),
        extra={"marginBottom": "20px", "padding": "14px 20px"},
    )

def kpi_row(boxes):
    return html.Div(boxes,
                    style={"display": "flex", "gap": "12px",
                           "flexWrap": "wrap", "marginBottom": "20px"})

def table_style(header_cols):
    head = html.Thead(html.Tr([
        html.Th(h, style={"color": MUTED, "padding": "6px 10px", "fontSize": "11px",
                          "textAlign": "right", "borderBottom": f"1px solid {BORDER}",
                          "whiteSpace": "nowrap"})
        for h in header_cols
    ]))
    return head

def make_table_row(cells):
    return html.Tr([
        html.Td(c["val"],
                style={"color": c.get("color", TEXT), "padding": "5px 10px",
                       "fontSize": "12px", "textAlign": "right",
                       "fontWeight": c.get("fw", "400"),
                       "borderTop": f"1px solid {BORDER}"})
        for c in cells
    ])

# ══════════════════════════════════════════════════════════════════════════════
#  PÁGINA 1 — INÍCIO

def _mini_nav(icon, title, desc):
    return html.Div([
        html.Span(icon, style={"fontSize": "18px"}),
        html.Div([
            html.P(title, style={"color": TEXT, "margin": "0", "fontWeight": "600", "fontSize": "13px"}),
            html.P(desc,  style={"color": MUTED, "margin": "0", "fontSize": "12px"}),
        ], style={"marginLeft": "10px"}),
    ], style={"display": "flex", "alignItems": "center"})
# ══════════════════════════════════════════════════════════════════════════════
page_home = html.Div([
    html.Div([
        html.Div([
            html.H1("IDH Brasil", style={"margin": "0", "fontSize": "34px",
                                         "fontWeight": "800", "color": TEXT}),
            html.P("Índice de Desenvolvimento Humano — dados reais & sintéticos",
                   style={"color": MUTED, "margin": "4px 0 0", "fontSize": "13px"}),
        ]),
        html.Div([
            html.Span("● Real",     style={"color": ACCENT, "fontSize": "13px", "marginRight": "14px"}),
            html.Span("● Sintético",style={"color": ORANGE, "fontSize": "13px"}),
        ]),
    ], style={"display": "flex", "justifyContent": "space-between",
              "alignItems": "center", "marginBottom": "22px"}),

    # Filtros
    filter_bar([
        _chip("Período:", range_slider("home-slider", ANO_MIN, ANO_MAX)),
    ]),

    # KPIs
    kpi_row([
        kpi_box("IDH início",           "home-kpi-start",  MUTED),
        kpi_box("IDH fim",              "home-kpi-end",    ACCENT),
        kpi_box("Variação IDH",         "home-kpi-var",    GREEN),
        kpi_box("Exp. Vida (máx.)",     "home-kpi-vida",   GREEN),
        kpi_box("Anos Escola (máx.)",   "home-kpi-escola", PURPLE),
        kpi_box("Registros Sintéticos", "home-kpi-fake",   ORANGE),
    ]),

    card([dcc.Graph(id="home-hero", config={"displayModeBar": False})],
         extra={"marginBottom": "20px"}),

    html.Div([
        card([
            html.H4("Sobre o Dashboard", style={"color": TEXT, "marginTop": 0, "fontSize": "14px"}),
            html.P("Painel com dados oficiais PNUD (1991–2021) e dataset sintético de 1.000 "
                   "registros. Use o controle de período para explorar qualquer intervalo.",
                   style={"color": MUTED, "lineHeight": "1.7", "fontSize": "13px"}),
            html.Hr(style={"borderColor": BORDER, "margin": "14px 0"}),
            html.Div([
                _mini_nav("📈", "IDH Geral",  "Séries temporais dos indicadores"),
                _mini_nav("⚥",  "Gêneros",    "Comparativo feminino vs masculino"),
                _mini_nav("🔮", "Cenários",   "Real × sintético com incerteza"),
            ], style={"display": "flex", "flexDirection": "column", "gap": "10px"}),
        ], extra={"flex": "1"}),
        card([
            html.H4("Resumo do Período", style={"color": TEXT, "marginTop": 0, "fontSize": "14px"}),
            html.Div(id="home-resumo"),
        ], extra={"flex": "1"}),
    ], style={"display": "flex", "gap": "16px"}),
], style={"padding": "28px"})

# ══════════════════════════════════════════════════════════════════════════════
#  PÁGINA 2 — IDH GERAL
# ══════════════════════════════════════════════════════════════════════════════
page_geral = html.Div([
    html.H2("IDH Geral", style={"color": TEXT, "margin": "0 0 4px", "fontSize": "24px"}),
    html.P("Evolução dos indicadores reais do Brasil",
           style={"color": MUTED, "margin": "0 0 20px", "fontSize": "13px"}),

    filter_bar([
        _chip("Período:",   range_slider("geral-slider", ANO_MIN, ANO_MAX)),
        _chip("Indicador:", _dd([
            {"label": "IDH Geral",          "value": "idh"},
            {"label": "Expectativa de Vida", "value": "expectativa_de_vida"},
            {"label": "Anos de Escola",      "value": "expectativa_de_anos_escola"},
        ], "idh", "geral-indicador", "210px")),
        _chip("Tipo:", _dd([
            {"label": "Linha",  "value": "linha"},
            {"label": "Área",   "value": "area"},
            {"label": "Barras", "value": "barras"},
        ], "linha", "geral-tipo", "120px")),
    ]),

    kpi_row([
        kpi_box("Início",   "geral-kpi-ini", MUTED),
        kpi_box("Fim",      "geral-kpi-fim", ACCENT),
        kpi_box("Variação", "geral-kpi-var", GREEN),
        kpi_box("Mínimo",   "geral-kpi-min", RED),
        kpi_box("Máximo",   "geral-kpi-max", PURPLE),
    ]),

    card([dcc.Graph(id="geral-main", config={"displayModeBar": False})],
         extra={"marginBottom": "20px"}),

    html.Div([
        card([dcc.Graph(id="geral-vida",   config={"displayModeBar": False})], extra={"flex": "1"}),
        card([dcc.Graph(id="geral-escola", config={"displayModeBar": False})], extra={"flex": "1"}),
    ], style={"display": "flex", "gap": "16px", "marginBottom": "20px"}),

    card([
        html.H4("Dados Filtrados", style={"color": TEXT, "marginTop": 0, "fontSize": "13px"}),
        html.Div(id="geral-tabela", style={"maxHeight": "260px", "overflowY": "auto"}),
    ]),
], style={"padding": "28px"})

# ══════════════════════════════════════════════════════════════════════════════
#  PÁGINA 3 — GÊNEROS
# ══════════════════════════════════════════════════════════════════════════════
page_generos = html.Div([
    html.H2("Análise por Gênero", style={"color": TEXT, "margin": "0 0 4px", "fontSize": "24px"}),
    html.P("IDH, expectativa de vida e escolaridade por gênero (dados a partir de 2002)",
           style={"color": MUTED, "margin": "0 0 20px", "fontSize": "13px"}),

    filter_bar([
        _chip("Período:", range_slider("gen-slider", ANOS_GENERO_MIN, ANO_MAX)),
        _chip("Séries:", dcc.Checklist(
            id="gen-series",
            options=[
                {"label": " Feminino",  "value": "fem"},
                {"label": " Masculino", "value": "masc"},
                {"label": " Geral",     "value": "geral"},
            ],
            value=["fem", "masc", "geral"],
            inline=True,
            inputStyle={"marginRight": "4px", "accentColor": ACCENT},
            labelStyle={"color": MUTED, "fontSize": "13px", "marginRight": "14px"},
        )),
        _chip("Indicador:", _dd([
            {"label": "IDH",                 "value": "idh"},
            {"label": "Expectativa de Vida",  "value": "vida"},
            {"label": "Anos de Escola",       "value": "escola"},
        ], "idh", "gen-indicador", "200px")),
    ]),

    kpi_row([
        kpi_box("IDH Fem. (fim)",   "gen-kpi-fem",   PURPLE),
        kpi_box("IDH Masc. (fim)",  "gen-kpi-masc",  ACCENT),
        kpi_box("Gap (Masc − Fem)", "gen-kpi-gap",   ORANGE),
        kpi_box("Vida Fem. (fim)",  "gen-kpi-vfem",  PURPLE),
        kpi_box("Vida Masc. (fim)", "gen-kpi-vmasc", ACCENT),
    ]),

    card([dcc.Graph(id="gen-linhas", config={"displayModeBar": False})],
         extra={"marginBottom": "20px"}),

    html.Div([
        card([dcc.Graph(id="gen-gap",    config={"displayModeBar": False})], extra={"flex": "1"}),
        card([dcc.Graph(id="gen-escola", config={"displayModeBar": False})], extra={"flex": "1"}),
    ], style={"display": "flex", "gap": "16px"}),
], style={"padding": "28px"})

# ══════════════════════════════════════════════════════════════════════════════
#  PÁGINA 4 — CENÁRIOS
# ══════════════════════════════════════════════════════════════════════════════
page_cenarios = html.Div([
    html.H2("Cenários — Real vs Sintético", style={"color": TEXT, "margin": "0 0 4px", "fontSize": "24px"}),
    html.P("Comparação entre dados reais e o dataset sintético (1.000 registros)",
           style={"color": MUTED, "margin": "0 0 20px", "fontSize": "13px"}),

    filter_bar([
        _chip("Período:", range_slider("cen-slider", ANO_MIN, ANO_MAX)),
        _chip("Agregação:", _dd([
            {"label": "Média",   "value": "mean"},
            {"label": "Mediana", "value": "median"},
            {"label": "Mínimo",  "value": "min"},
            {"label": "Máximo",  "value": "max"},
        ], "mean", "cen-agr", "140px")),
        _chip("Banda:", dcc.Slider(
            id="cen-sigma", min=0.5, max=2.0, step=0.5, value=1.0,
            marks={v: {"label": f"{v}σ", "style": {"color": MUTED, "fontSize": "11px"}}
                   for v in [0.5, 1.0, 1.5, 2.0]},
            tooltip={"placement": "bottom", "always_visible": False},
        )),
        _chip("Incerteza:", dcc.Checklist(
            id="cen-banda",
            options=[{"label": " Exibir", "value": "show"}],
            value=["show"],
            inputStyle={"marginRight": "4px", "accentColor": ACCENT},
            labelStyle={"color": MUTED, "fontSize": "13px"},
        )),
    ]),

    kpi_row([
        kpi_box("IDH Real (média)",     "cen-kpi-real", ACCENT),
        kpi_box("IDH Sint. (agr.)",     "cen-kpi-fake", ORANGE),
        kpi_box("Diferença de Médias",  "cen-kpi-diff", RED),
        kpi_box("Desvio Padrão Sint.",  "cen-kpi-std",  PURPLE),
        kpi_box("Registros no Período", "cen-kpi-n",    MUTED),
    ]),

    card([dcc.Graph(id="cen-compare", config={"displayModeBar": False})],
         extra={"marginBottom": "20px"}),

    html.Div([
        card([dcc.Graph(id="cen-scatter", config={"displayModeBar": False})], extra={"flex": "1"}),
        card([dcc.Graph(id="cen-vida",    config={"displayModeBar": False})], extra={"flex": "1"}),
    ], style={"display": "flex", "gap": "16px", "marginBottom": "20px"}),

    card([dcc.Graph(id="cen-box", config={"displayModeBar": False})]),
], style={"padding": "28px"})

# ══════════════════════════════════════════════════════════════════════════════
#  APP + LAYOUT
# ══════════════════════════════════════════════════════════════════════════════
NAV_ITEMS = [
    {"id": "home",     "label": "🏠  Início",    "page": page_home},
    {"id": "geral",    "label": "📈  IDH Geral",  "page": page_geral},
    {"id": "generos",  "label": "⚥  Gêneros",    "page": page_generos},
    {"id": "cenarios", "label": "🔮  Cenários",   "page": page_cenarios},
]

app = dash.Dash(__name__, suppress_callback_exceptions=True)

app.layout = html.Div([
    dcc.Store(id="active-page", data="home"),

    # Sidebar
    html.Div([
        html.Div([
            html.Div("IDH",    style={"fontSize": "22px", "fontWeight": "800", "color": ACCENT}),
            html.Div("Brasil", style={"fontSize": "10px", "color": MUTED,
                                      "letterSpacing": "3px", "textTransform": "uppercase"}),
        ], style={"padding": "24px 20px 18px", "borderBottom": f"1px solid {BORDER}"}),

        html.Div([
            html.Button(
                item["label"], id=f"nav-{item['id']}", n_clicks=0,
                style={"width": "100%", "textAlign": "left", "background": "transparent",
                       "border": "none", "color": MUTED, "fontSize": "13px",
                       "padding": "11px 20px", "cursor": "pointer",
                       "borderRadius": "8px", "marginBottom": "3px", "fontFamily": FONT},
            )
            for item in NAV_ITEMS
        ], style={"padding": "12px 8px"}),

        html.Div([
            html.P("PNUD · Brasil", style={"color": MUTED, "fontSize": "10px", "margin": "0"}),
            html.P("1991 – 2021",   style={"color": MUTED, "fontSize": "10px", "margin": "2px 0 0"}),
        ], style={"padding": "0 20px 24px", "marginTop": "auto"}),
    ], style={
        "width": "220px", "minWidth": "220px", "background": CARD,
        "borderRight": f"1px solid {BORDER}",
        "height": "100vh", "position": "fixed", "left": 0, "top": 0,
        "zIndex": 100, "overflowY": "auto",
        "display": "flex", "flexDirection": "column",
    }),

    html.Div(id="page-content", style={
        "marginLeft": "220px", "minHeight": "100vh",
        "background": BG, "overflowY": "auto",
    }),
], style={"display": "flex", "background": BG, "fontFamily": FONT,
          "color": TEXT, "minHeight": "100vh"})


# ══════════════════════════════════════════════════════════════════════════════
#  CALLBACK — NAVEGAÇÃO
# ══════════════════════════════════════════════════════════════════════════════
@app.callback(
    Output("page-content", "children"),
    Output("active-page",  "data"),
    *[Output(f"nav-{i['id']}", "style") for i in NAV_ITEMS],
    *[Input(f"nav-{i['id']}", "n_clicks") for i in NAV_ITEMS],
    Input("active-page", "data"),
    prevent_initial_call=False,
)
def switch_page(*args):
    active = args[-1]
    ctx = dash.callback_context
    if ctx.triggered and ctx.triggered[0]["prop_id"] != "active-page.data":
        active = ctx.triggered[0]["prop_id"].split(".")[0].replace("nav-", "")

    pages = {i["id"]: i["page"] for i in NAV_ITEMS}

    def nav_style(iid):
        on = iid == active
        return {
            "width": "100%", "textAlign": "left",
            "background": "rgba(88,166,255,0.12)" if on else "transparent",
            "border": "none",
            "color": ACCENT if on else MUTED,
            "fontSize": "13px", "padding": "11px 20px",
            "cursor": "pointer", "borderRadius": "8px", "marginBottom": "3px",
            "fontWeight": "600" if on else "400", "fontFamily": FONT,
            "borderLeft": f"3px solid {ACCENT}" if on else "3px solid transparent",
        }

    return pages.get(active, page_home), active, *[nav_style(i["id"]) for i in NAV_ITEMS]


# ══════════════════════════════════════════════════════════════════════════════
#  CALLBACKS — INÍCIO
# ══════════════════════════════════════════════════════════════════════════════
@app.callback(
    Output("home-kpi-start",  "children"),
    Output("home-kpi-end",    "children"),
    Output("home-kpi-var",    "children"),
    Output("home-kpi-vida",   "children"),
    Output("home-kpi-escola", "children"),
    Output("home-kpi-fake",   "children"),
    Output("home-hero",       "figure"),
    Output("home-resumo",     "children"),
    Input("home-slider", "value"),
)
def cb_home(rng):
    a, b = rng
    dr = df_real[(df_real["ano_referencia"] >= a) & (df_real["ano_referencia"] <= b)]
    df = df_fake[(df_fake["ano_referencia"] >= a) & (df_fake["ano_referencia"] <= b)]

    i0 = dr["idh"].iloc[0]  if len(dr) else 0
    i1 = dr["idh"].iloc[-1] if len(dr) else 0
    var = (i1 / i0 - 1) * 100 if i0 else 0

    fake_agg = df.groupby("ano_referencia")["idh"].mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dr["ano_referencia"], y=dr["idh"],
        mode="lines+markers", name="IDH Real",
        line=dict(color=ACCENT, width=3), marker=dict(size=5),
        fill="tozeroy", fillcolor="rgba(88,166,255,0.07)",
    ))
    fig.add_trace(go.Scatter(
        x=fake_agg.index, y=fake_agg.values,
        mode="lines", name="IDH Sintético (média)",
        line=dict(color=ORANGE, width=2, dash="dot"),
    ))
    fig.update_layout(**LBASE, title=f"Evolução do IDH — {a} a {b}", height=280)

    rows_data = [
        ("Variação IDH",         f"+{var:.1f}%"),
        ("Exp. Vida — início",   f"{dr['expectativa_de_vida'].iloc[0]:.1f} anos"  if len(dr) else "–"),
        ("Exp. Vida — fim",      f"{dr['expectativa_de_vida'].iloc[-1]:.1f} anos" if len(dr) else "–"),
        ("Anos Escola — início", f"{dr['expectativa_de_anos_escola'].iloc[0]:.1f}"  if len(dr) else "–"),
        ("Anos Escola — fim",    f"{dr['expectativa_de_anos_escola'].iloc[-1]:.1f}" if len(dr) else "–"),
        ("Registros sintéticos", f"{len(df):,}".replace(",", ".")),
    ]
    table = html.Table([
        html.Thead(html.Tr([
            html.Th("Métrica", style={"color": MUTED, "fontSize": "11px", "paddingBottom": "8px"}),
            html.Th("Valor",   style={"color": MUTED, "fontSize": "11px", "paddingBottom": "8px", "textAlign": "right"}),
        ])),
        html.Tbody([
            html.Tr([
                html.Td(r, style={"color": MUTED, "padding": "5px 0", "fontSize": "13px"}),
                html.Td(v, style={"color": TEXT,  "padding": "5px 0", "fontSize": "13px", "textAlign": "right"}),
            ], style={"borderTop": f"1px solid {BORDER}"})
            for r, v in rows_data
        ]),
    ], style={"width": "100%", "borderCollapse": "collapse"})

    return (
        f"{i0:.3f}", f"{i1:.3f}", f"+{var:.1f}%",
        f"{dr['expectativa_de_vida'].max():.1f} anos" if len(dr) else "–",
        f"{dr['expectativa_de_anos_escola'].max():.1f}" if len(dr) else "–",
        f"{len(df):,}".replace(",", "."),
        fig, table,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  CALLBACKS — IDH GERAL
# ══════════════════════════════════════════════════════════════════════════════
_IND = {
    "idh":                        ("IDH",              "{:.3f}", ACCENT),
    "expectativa_de_vida":         ("Exp. Vida (anos)", "{:.1f}", GREEN),
    "expectativa_de_anos_escola":  ("Anos de Escola",   "{:.1f}", PURPLE),
}

@app.callback(
    Output("geral-kpi-ini",  "children"),
    Output("geral-kpi-fim",  "children"),
    Output("geral-kpi-var",  "children"),
    Output("geral-kpi-min",  "children"),
    Output("geral-kpi-max",  "children"),
    Output("geral-main",     "figure"),
    Output("geral-vida",     "figure"),
    Output("geral-escola",   "figure"),
    Output("geral-tabela",   "children"),
    Input("geral-slider",    "value"),
    Input("geral-indicador", "value"),
    Input("geral-tipo",      "value"),
)
def cb_geral(rng, indicador, tipo):
    a, b = rng
    dr = df_real[(df_real["ano_referencia"] >= a) & (df_real["ano_referencia"] <= b)]
    label, fmt, color = _IND[indicador]
    col = dr[indicador]

    ini = fmt.format(col.iloc[0])  if len(dr) else "–"
    fim = fmt.format(col.iloc[-1]) if len(dr) else "–"
    var = f"{((col.iloc[-1]/col.iloc[0]-1)*100):+.1f}%" if len(dr) > 1 and col.iloc[0] else "–"
    mn  = fmt.format(col.min()) if len(dr) else "–"
    mx  = fmt.format(col.max()) if len(dr) else "–"

    fig_main = go.Figure()
    if tipo == "linha":
        fig_main.add_trace(go.Scatter(
            x=dr["ano_referencia"], y=dr[indicador], mode="lines+markers",
            line=dict(color=color, width=3), marker=dict(size=5), name=label,
        ))
    elif tipo == "area":
        fig_main.add_trace(go.Scatter(
            x=dr["ano_referencia"], y=dr[indicador], mode="lines",
            line=dict(color=color, width=2), name=label,
            fill="tozeroy", fillcolor=f"rgba(88,166,255,0.08)",
        ))
    elif tipo == "barras":
        avg = col.mean()
        fig_main.add_trace(go.Bar(
            x=dr["ano_referencia"], y=dr[indicador],
            marker_color=[color if v >= avg else MUTED for v in dr[indicador]],
            name=label,
        ))
    fig_main.update_layout(**LBASE, title=f"{label} — {a} a {b}", height=300)

    # Mini expectativa de vida
    fig_vida = go.Figure()
    fig_vida.add_trace(go.Scatter(x=dr["ano_referencia"], y=dr["expectativa_de_vida"],
                                  mode="lines+markers", name="Geral",
                                  line=dict(color=GREEN, width=2), marker=dict(size=4)))
    fig_vida.add_trace(go.Scatter(x=dr["ano_referencia"], y=dr["expectativa_de_vida_feminina"],
                                  mode="lines", name="Feminina",
                                  line=dict(color=PURPLE, width=1.5, dash="dash")))
    fig_vida.add_trace(go.Scatter(x=dr["ano_referencia"], y=dr["expectativa_de_vida_masculina"],
                                  mode="lines", name="Masculina",
                                  line=dict(color=ACCENT, width=1.5, dash="dot")))
    fig_vida.update_layout(**LBASE, title="Expectativa de Vida (anos)", height=250)

    # Mini anos de escola
    avg_esc = dr["expectativa_de_anos_escola"].mean()
    fig_esc = go.Figure()
    fig_esc.add_trace(go.Bar(
        x=dr["ano_referencia"], y=dr["expectativa_de_anos_escola"],
        marker_color=[PURPLE if v >= avg_esc else MUTED for v in dr["expectativa_de_anos_escola"]],
        name="Anos esperados",
    ))
    fig_esc.update_layout(**LBASE, title="Anos Esperados de Escola", height=250)

    # Tabela
    table = html.Table([
        html.Thead(html.Tr([
            html.Th(h, style={"color": MUTED, "padding": "6px 10px", "fontSize": "11px",
                              "textAlign": "right", "borderBottom": f"1px solid {BORDER}"})
            for h in ["Ano", "IDH", "Exp. Vida", "Anos Escola"]
        ])),
        html.Tbody([
            html.Tr([
                html.Td(str(int(row["ano_referencia"])),
                        style={"color": TEXT, "padding": "5px 10px", "fontSize": "12px", "textAlign": "right"}),
                html.Td(f"{row['idh']:.3f}",
                        style={"color": ACCENT, "padding": "5px 10px", "fontSize": "12px",
                               "fontWeight": "700", "textAlign": "right"}),
                html.Td(f"{row['expectativa_de_vida']:.1f}",
                        style={"color": TEXT, "padding": "5px 10px", "fontSize": "12px", "textAlign": "right"}),
                html.Td(f"{row['expectativa_de_anos_escola']:.1f}",
                        style={"color": TEXT, "padding": "5px 10px", "fontSize": "12px", "textAlign": "right"}),
            ], style={"borderTop": f"1px solid {BORDER}"})
            for _, row in dr.iterrows()
        ]),
    ], style={"width": "100%", "borderCollapse": "collapse"})

    return ini, fim, var, mn, mx, fig_main, fig_vida, fig_esc, table


# ══════════════════════════════════════════════════════════════════════════════
#  CALLBACKS — GÊNEROS
# ══════════════════════════════════════════════════════════════════════════════
@app.callback(
    Output("gen-kpi-fem",   "children"),
    Output("gen-kpi-masc",  "children"),
    Output("gen-kpi-gap",   "children"),
    Output("gen-kpi-vfem",  "children"),
    Output("gen-kpi-vmasc", "children"),
    Output("gen-linhas",    "figure"),
    Output("gen-gap",       "figure"),
    Output("gen-escola",    "figure"),
    Input("gen-slider",    "value"),
    Input("gen-series",    "value"),
    Input("gen-indicador", "value"),
)
def cb_generos(rng, series, indicador):
    a, b = rng
    dr = df_real[
        (df_real["ano_referencia"] >= a) &
        (df_real["ano_referencia"] <= b) &
        (df_real["idh_feminino"] > 0)
    ].copy()

    kpi_fem  = f"{dr['idh_feminino'].iloc[-1]:.3f}"  if len(dr) else "–"
    kpi_masc = f"{dr['idh_masculino'].iloc[-1]:.3f}" if len(dr) else "–"
    gap_v    = dr['idh_masculino'].iloc[-1] - dr['idh_feminino'].iloc[-1] if len(dr) else 0
    kpi_gap  = f"{gap_v:+.4f}" if len(dr) else "–"
    kpi_vf   = f"{dr['expectativa_de_vida_feminina'].iloc[-1]:.1f} anos"  if len(dr) else "–"
    kpi_vm   = f"{dr['expectativa_de_vida_masculina'].iloc[-1]:.1f} anos" if len(dr) else "–"

    _cols = {
        "idh":    ("idh_feminino",                      "idh_masculino",                     "idh"),
        "vida":   ("expectativa_de_vida_feminina",       "expectativa_de_vida_masculina",      "expectativa_de_vida"),
        "escola": ("expectativa_de_anos_escola_feminina","expectativa_de_anos_escola_masculina","expectativa_de_anos_escola"),
    }
    _labs = {
        "idh":    ("IDH Feminino",  "IDH Masculino",  "IDH Geral"),
        "vida":   ("Vida Feminina", "Vida Masculina", "Vida Geral"),
        "escola": ("Escola Fem.",   "Escola Masc.",   "Escola Geral"),
    }
    col_f, col_m, col_g = _cols[indicador]
    lab_f, lab_m, lab_g = _labs[indicador]

    fig_lin = go.Figure()
    if "fem" in (series or []):
        fig_lin.add_trace(go.Scatter(x=dr["ano_referencia"], y=dr[col_f],
                                     name=lab_f, mode="lines+markers",
                                     line=dict(color=PURPLE, width=3), marker=dict(size=5)))
    if "masc" in (series or []):
        fig_lin.add_trace(go.Scatter(x=dr["ano_referencia"], y=dr[col_m],
                                     name=lab_m, mode="lines+markers",
                                     line=dict(color=ACCENT, width=3), marker=dict(size=5)))
    if "geral" in (series or []):
        fig_lin.add_trace(go.Scatter(x=dr["ano_referencia"], y=dr[col_g],
                                     name=lab_g, mode="lines",
                                     line=dict(color=MUTED, width=2, dash="dot")))
    fig_lin.update_layout(**LBASE, title=f"{lab_f.split()[0]} por Gênero — {a} a {b}", height=300)

    gap = dr["idh_masculino"] - dr["idh_feminino"]
    fig_gap = go.Figure()
    fig_gap.add_trace(go.Bar(
        x=dr["ano_referencia"], y=gap,
        marker_color=[GREEN if v >= 0 else RED for v in gap],
        name="Gap IDH",
    ))
    fig_gap.add_hline(y=0, line_color=MUTED, line_width=1)
    fig_gap.update_layout(**LBASE, title="Gap IDH Masculino − Feminino", height=260)

    dr_e = dr[dr["expectativa_de_anos_escola_feminina"] > 0]
    fig_esc = go.Figure()
    fig_esc.add_trace(go.Bar(x=dr_e["ano_referencia"], y=dr_e["expectativa_de_anos_escola_feminina"],
                             name="Feminino", marker_color=PURPLE))
    fig_esc.add_trace(go.Bar(x=dr_e["ano_referencia"], y=dr_e["expectativa_de_anos_escola_masculina"],
                             name="Masculino", marker_color=ACCENT))
    fig_esc.update_layout(**LBASE, title="Anos de Escola por Gênero", barmode="group", height=260)

    return kpi_fem, kpi_masc, kpi_gap, kpi_vf, kpi_vm, fig_lin, fig_gap, fig_esc


# ══════════════════════════════════════════════════════════════════════════════
#  CALLBACKS — CENÁRIOS
# ══════════════════════════════════════════════════════════════════════════════
@app.callback(
    Output("cen-kpi-real",  "children"),
    Output("cen-kpi-fake",  "children"),
    Output("cen-kpi-diff",  "children"),
    Output("cen-kpi-std",   "children"),
    Output("cen-kpi-n",     "children"),
    Output("cen-compare",   "figure"),
    Output("cen-scatter",   "figure"),
    Output("cen-vida",      "figure"),
    Output("cen-box",       "figure"),
    Input("cen-slider", "value"),
    Input("cen-agr",    "value"),
    Input("cen-sigma",  "value"),
    Input("cen-banda",  "value"),
)
def cb_cenarios(rng, agr, sigma, banda):
    a, b = rng
    dr = df_real[(df_real["ano_referencia"] >= a) & (df_real["ano_referencia"] <= b)]
    df = df_fake[(df_fake["ano_referencia"] >= a) & (df_fake["ano_referencia"] <= b)]

    fn = {"mean": "mean", "median": "median", "min": "min", "max": "max"}.get(agr, "mean")
    fake_agg = df.groupby("ano_referencia").agg(
        idh_agr   =("idh", fn),
        idh_std   =("idh", "std"),
        vida_agr  =("expectativa_de_vida", fn),
    ).reset_index()

    real_m  = dr["idh"].mean()   if len(dr) else 0
    fake_m  = fake_agg["idh_agr"].mean() if len(fake_agg) else 0
    diff    = abs(real_m - fake_m)
    std_v   = df["idh"].std()    if len(df) else 0

    agr_l = {"mean": "Média", "median": "Mediana", "min": "Mínimo", "max": "Máximo"}[agr]

    # Comparação com banda
    fig_cmp = go.Figure()
    if "show" in (banda or []) and len(fake_agg):
        upper = fake_agg["idh_agr"] + sigma * fake_agg["idh_std"].fillna(0)
        lower = fake_agg["idh_agr"] - sigma * fake_agg["idh_std"].fillna(0)
        fig_cmp.add_trace(go.Scatter(
            x=fake_agg["ano_referencia"], y=upper,
            mode="lines", line=dict(width=0), showlegend=False))
        fig_cmp.add_trace(go.Scatter(
            x=fake_agg["ano_referencia"], y=lower,
            mode="lines", line=dict(width=0),
            fill="tonexty", fillcolor="rgba(255,140,66,0.13)",
            name=f"Banda ±{sigma}σ"))
    fig_cmp.add_trace(go.Scatter(
        x=fake_agg["ano_referencia"], y=fake_agg["idh_agr"],
        name=f"Sintético ({agr_l})", mode="lines",
        line=dict(color=ORANGE, width=2, dash="dash")))
    fig_cmp.add_trace(go.Scatter(
        x=dr["ano_referencia"], y=dr["idh"],
        name="IDH Real", mode="lines+markers",
        line=dict(color=ACCENT, width=3), marker=dict(size=5)))
    fig_cmp.update_layout(**LBASE,
                          title=f"IDH Real vs Sintético ({agr_l}) — {a} a {b}", height=300)

    # Scatter correlação
    merged = dr.merge(fake_agg, on="ano_referencia", how="inner")
    fig_sc = go.Figure()
    if len(merged):
        lims = [min(merged["idh"].min(), merged["idh_agr"].min()) - 0.005,
                max(merged["idh"].max(), merged["idh_agr"].max()) + 0.005]
        fig_sc.add_trace(go.Scatter(x=lims, y=lims, mode="lines",
                                    line=dict(color=RED, width=1, dash="dot"), name="1:1"))
        fig_sc.add_trace(go.Scatter(
            x=merged["idh"], y=merged["idh_agr"],
            mode="markers+text", name="Ano",
            text=merged["ano_referencia"].astype(str),
            textposition="top center", textfont=dict(size=9, color=MUTED),
            marker=dict(size=8, color=ACCENT, opacity=0.85),
        ))
    fig_sc.update_layout(**LBASE, title=f"Correlação: Real × Sintético ({agr_l})",
                         xaxis_title="IDH Real", yaxis_title=f"IDH Sintético ({agr_l})", height=280)

    # Vida comparada
    fig_vida = go.Figure()
    fig_vida.add_trace(go.Scatter(x=dr["ano_referencia"], y=dr["expectativa_de_vida"],
                                  name="Real", mode="lines+markers",
                                  line=dict(color=ACCENT, width=2), marker=dict(size=4)))
    fig_vida.add_trace(go.Scatter(x=fake_agg["ano_referencia"], y=fake_agg["vida_agr"],
                                  name=f"Sintético ({agr_l})", mode="lines",
                                  line=dict(color=ORANGE, width=2, dash="dash")))
    fig_vida.update_layout(**LBASE, title="Expectativa de Vida: Real vs Sintético", height=280)

    # Boxplot (máx 12 anos para legibilidade)
    anos_box = sorted(df["ano_referencia"].unique())
    step = max(1, len(anos_box) // 12)
    fig_box = go.Figure()
    for ano in anos_box[::step]:
        sub = df[df["ano_referencia"] == ano]["idh"].dropna()
        if len(sub):
            fig_box.add_trace(go.Box(y=sub, name=str(ano), marker_color=PURPLE,
                                     line_color=PURPLE, showlegend=False, boxmean="sd"))
    fig_box.update_layout(**LBASE, title="Distribuição IDH Sintético por Ano",
                          xaxis_title="Ano", yaxis_title="IDH", height=280)

    return (
        f"{real_m:.3f}", f"{fake_m:.3f}", f"{diff:.4f}", f"{std_v:.3f}",
        f"{len(df):,}".replace(",", "."),
        fig_cmp, fig_sc, fig_vida, fig_box,
    )


if __name__ == "__main__":
    app.run(debug=False, port=8050)
