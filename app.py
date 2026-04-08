# ── Patch de compatibilidade: comm x Dash 4.x ────────────────────────────────
try:
    import comm as _comm
    _orig_cc = _comm.create_comm
    def _safe_cc(**kw):
        try:
            return _orig_cc(**kw)
        except Exception:
            from unittest.mock import MagicMock
            return MagicMock()
    _comm.create_comm = _safe_cc
except Exception:
    pass
# ─────────────────────────────────────────────────────────────────────────────

import dash
from dash import dcc, html, Input, Output, callback_context
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import os

# ══════════════════════════════════════════════════════════════════════════════
#  DADOS — carregamento robusto
# ══════════════════════════════════════════════════════════════════════════════
_BASE = os.path.dirname(os.path.abspath(__file__))

try:
    df_real = pd.read_csv(os.path.join(_BASE, "dados", "idh.csv"))
except FileNotFoundError:
    raise SystemExit("ERRO: dados/idh.csv não encontrado.")

try:
    df_fake = pd.read_csv(os.path.join(_BASE, "dados", "idh_sintetico.csv"))
    for _col in df_fake.columns:
        if _col != "ano_referencia":
            df_fake[_col] = (df_fake[_col].astype(str)
                             .str.replace(",", ".", regex=False))
            df_fake[_col] = pd.to_numeric(df_fake[_col], errors="coerce")
    df_fake = df_fake.sort_values("ano_referencia").reset_index(drop=True)
except FileNotFoundError:
    raise SystemExit("ERRO: dados/idh_sintetico.csv não encontrado.")

# Derivar limites de anos a partir dos próprios dados (sem hardcode)
ANO_MIN         = int(df_real["ano_referencia"].min())
ANO_MAX         = int(df_real["ano_referencia"].max())
ANOS_GENERO_MIN = int(df_real.loc[df_real["idh_feminino"] > 0, "ano_referencia"].min())

# Pré-computar para storytelling
_IDH_1991 = df_real["idh"].iloc[0]
_IDH_2021 = df_real["idh"].iloc[-1]
_IDH_CRESC = (_IDH_2021 / _IDH_1991 - 1) * 100
_VIDA_FEM  = df_real.loc[df_real["expectativa_de_vida_feminina"] > 0, "expectativa_de_vida_feminina"].iloc[-1]
_VIDA_MASC = df_real.loc[df_real["expectativa_de_vida_masculina"] > 0, "expectativa_de_vida_masculina"].iloc[-1]
_GAP_VIDA  = _VIDA_FEM - _VIDA_MASC
_IDH_2020  = df_real.loc[df_real["ano_referencia"] == 2020, "idh"].values[0] if 2020 in df_real["ano_referencia"].values else None
_IDH_2019  = df_real.loc[df_real["ano_referencia"] == 2019, "idh"].values[0] if 2019 in df_real["ano_referencia"].values else None

# ══════════════════════════════════════════════════════════════════════════════
#  PALETA — profissional, data viz sênior (inspirada em Tableau / Observable)
# ══════════════════════════════════════════════════════════════════════════════
BG      = "#0A0E1A"   # Navy black — fundo geral
SURF    = "#111827"   # Card base
SURF2   = "#1C2333"   # Card elevado / hover
BORDER  = "#1E2D4A"   # Borda sutil navy
TEXT    = "#E2E8F0"   # Slate-200 — texto principal (não branco puro)
MUTED   = "#64748B"   # Slate-500 — texto secundário
BLUE    = "#3B82F6"   # Blue-500 — principal, confiável
TEAL    = "#06B6D4"   # Cyan-500 — destaque / linha real
GREEN   = "#10B981"   # Emerald-500 — positivo / crescimento
PURPLE  = "#8B5CF6"   # Violet-500 — feminino / secundário
AMBER   = "#F59E0B"   # Amber-500 — sintético / aviso
ROSE    = "#EF4444"   # Red-500 — negativo / queda
FONT    = "'Inter','Segoe UI',sans-serif"

# Sequência para múltiplas séries (ordem de uso nos gráficos)
PALETTE = [TEAL, PURPLE, AMBER, GREEN, ROSE, BLUE]

def rgba(hex_color, alpha):
    """Converte hex + alpha para rgba string."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ══════════════════════════════════════════════════════════════════════════════
#  BASE LAYOUT DOS GRÁFICOS
# ══════════════════════════════════════════════════════════════════════════════
def base_layout(title="", height=320, **overrides):
    d = dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor ="rgba(0,0,0,0)",
        font=dict(color=TEXT, family=FONT, size=12),
        title=dict(text=title, font=dict(size=14, color=TEXT), x=0.01, xref="paper"),
        margin=dict(l=52, r=24, t=52, b=52),
        xaxis=dict(
            gridcolor=rgba(BORDER, 0.8),
            zerolinecolor=BORDER,
            linecolor=BORDER,
            tickfont=dict(color=MUTED, size=11),
            showgrid=True,
        ),
        yaxis=dict(
            gridcolor=rgba(BORDER, 0.8),
            zerolinecolor=BORDER,
            linecolor=BORDER,
            tickfont=dict(color=MUTED, size=11),
            showgrid=True,
        ),
        legend=dict(
            orientation="h", y=-0.18,
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=MUTED, size=11),
            bordercolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(
            bgcolor=SURF2,
            font_color=TEXT,
            bordercolor=BLUE,
            font_size=12,
            font_family=FONT,
        ),
        height=height,
    )
    d.update(overrides)
    return d


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS DE UI
# ══════════════════════════════════════════════════════════════════════════════
def _safe_val(series, idx=-1, fmt="{:.3f}", fallback="—"):
    """Retorna valor formatado de forma segura, sem NaN."""
    try:
        v = series.dropna().iloc[idx]
        return fmt.format(v)
    except Exception:
        return fallback


def page_title(title, subtitle=""):
    """Cabeçalho de página com título e subtítulo de contexto."""
    children = [
        html.H2(title, style={
            "margin": "0 0 6px",
            "fontSize": "22px",
            "fontWeight": "700",
            "color": TEXT,
            "letterSpacing": "-0.3px",
            "lineHeight": "1.3",
        }),
    ]
    if subtitle:
        children.append(html.P(subtitle, style={
            "color": MUTED,
            "margin": "0 0 22px",
            "fontSize": "13px",
            "lineHeight": "1.6",
            "maxWidth": "720px",
        }))
    return html.Div(children)


def insight_card(text, color=BLUE, icon="💡"):
    """Callout box de achado analítico."""
    return html.Div([
        html.Span(icon, style={"fontSize": "15px", "flexShrink": "0",
                               "marginTop": "1px", "color": TEXT}),
        html.Span(text, className="insight-text", style={
            "color": TEXT,
            "fontSize": "13px",
            "lineHeight": "1.6",
            "display": "block",
        }),
    ], style={
        "display": "flex",
        "alignItems": "flex-start",
        "gap": "10px",
        "background": rgba(color, 0.10),
        "border": f"1px solid {rgba(color, 0.30)}",
        "borderLeft": f"3px solid {color}",
        "borderRadius": "8px",
        "padding": "11px 14px",
        "marginBottom": "16px",
        "color": TEXT,          # força herança correta no Chrome dark mode
    })


def kpi_card(label, value_id, color=TEAL, icon=""):
    """KPI card sem webkit-gradient (seguro em qualquer browser/dark mode)."""
    return html.Div([
        html.Div([
            html.Span(icon + " " if icon else "", style={
                "fontSize": "13px", "color": color,
            }),
            html.Span(label, style={
                "color": MUTED,
                "fontSize": "10px",
                "textTransform": "uppercase",
                "letterSpacing": "0.8px",
                "fontWeight": "600",
            }),
        ], style={"display": "flex", "alignItems": "center",
                  "gap": "4px", "marginBottom": "10px"}),
        html.Div(id=value_id, children="—", style={
            "color": color,
            "fontSize": "24px",
            "fontWeight": "800",
            "letterSpacing": "-0.5px",
            "lineHeight": "1",
        }),
    ], style={
        "background": SURF,
        "border": f"1px solid {BORDER}",
        "borderTop": f"3px solid {color}",
        "borderRadius": "10px",
        "padding": "16px 18px",
        "flex": "1",
        "minWidth": "130px",
        "maxWidth": "220px",
    })


def kpi_row(cards):
    return html.Div(cards, style={
        "display": "flex",
        "gap": "10px",
        "flexWrap": "wrap",
        "marginBottom": "22px",
    })


def chart_card(children, extra=None):
    s = {
        "background": SURF,
        "border": f"1px solid {BORDER}",
        "borderRadius": "12px",
        "overflow": "hidden",
        "boxShadow": f"0 2px 16px {rgba(BG, 0.8)}",
    }
    if extra:
        s.update(extra)
    return html.Div(children, style=s)


def filter_bar(children):
    return html.Div([
        html.Div(children, style={
            "display": "flex",
            "alignItems": "center",   # ← center, não flex-end
            "gap": "28px",
            "flexWrap": "wrap",
        }),
    ], style={
        "background": SURF,
        "border": f"1px solid {BORDER}",
        "borderRadius": "10px",
        "padding": "14px 20px",
        "marginBottom": "22px",
    })


def filter_label(label):
    return html.Span(label, style={
        "color": MUTED,
        "fontSize": "11px",
        "fontWeight": "600",
        "textTransform": "uppercase",
        "letterSpacing": "0.5px",
        "whiteSpace": "nowrap",
        "marginRight": "8px",
    })


def filter_group(label, control):
    return html.Div([
        filter_label(label),
        control,
    ], style={"display": "flex", "alignItems": "center", "gap": "0"})


def styled_dd(options, value, id_, width="200px"):
    return dcc.Dropdown(
        id=id_, options=options, value=value, clearable=False,
        className="dash-dd",
        style={
            "width": width,
            "fontSize": "13px",
            "fontFamily": FONT,
            # Forçar cor do texto diretamente no container
            "color": "#111827",
        },
    )


def year_range_picker(id_, mn, mx):
    """Dois dropdowns de ano — sem sliders, sem bolinhas, visual limpo."""
    anos = list(range(mn, mx + 1))
    opts = [{"label": str(a), "value": a} for a in anos]
    dd_style = {
        "width": "90px",
        "fontSize": "13px",
        "fontFamily": FONT,
        "color": "#111827",
    }
    return html.Div([
        dcc.Dropdown(id=f"{id_}-start", options=opts, value=mn,
                     clearable=False, style=dd_style, className="dash-dd"),
        html.Span("→", style={
            "color": TEXT, "fontSize": "14px",
            "margin": "0 8px", "userSelect": "none",
        }),
        dcc.Dropdown(id=f"{id_}-end", options=opts, value=mx,
                     clearable=False, style=dd_style, className="dash-dd"),
    ], style={"display": "flex", "alignItems": "center"})


def data_table(header_cols, rows_data):
    """Tabela de dados estilizada."""
    th = {
        "color": MUTED, "padding": "8px 14px",
        "fontSize": "11px", "textAlign": "right",
        "borderBottom": f"2px solid {BORDER}",
        "textTransform": "uppercase", "letterSpacing": "0.4px",
        "fontWeight": "600", "whiteSpace": "nowrap",
        "background": SURF2,
    }
    return html.Table([
        html.Thead(html.Tr([html.Th(h, style=th) for h in header_cols])),
        html.Tbody(rows_data),
    ], style={"width": "100%", "borderCollapse": "collapse"})


def table_row(cells, striped=False):
    bg = rgba(SURF2, 0.5) if striped else "transparent"
    return html.Tr([
        html.Td(c["val"], style={
            "color": c.get("color", TEXT),
            "padding": "7px 14px",
            "fontSize": "12px",
            "textAlign": "right",
            "fontWeight": c.get("fw", "400"),
            "borderTop": f"1px solid {BORDER}",
            "background": bg,
        }) for c in cells
    ])


# ══════════════════════════════════════════════════════════════════════════════
#  PÁGINA 1 — INÍCIO / PANORAMA GERAL
# ══════════════════════════════════════════════════════════════════════════════
_covid_insight = (
    f"Em 2020, a pandemia de COVID-19 reverteu anos de progresso: o IDH caiu de "
    f"{_IDH_2019:.3f} (2019) para {_IDH_2020:.3f} (2020)"
    if _IDH_2020 and _IDH_2019 else ""
)

page_home = html.Div([

    # Cabeçalho
    html.Div([
        html.Div([
            html.Div("IDH Brasil", style={
                "fontSize": "32px", "fontWeight": "800",
                "color": TEXT, "letterSpacing": "-1px",
                "lineHeight": "1",
            }),
            html.Div("Índice de Desenvolvimento Humano · PNUD 1991–2021", style={
                "color": MUTED, "fontSize": "13px", "marginTop": "6px",
            }),
        ]),
        html.Div([
            html.Span("● Dados Reais PNUD",
                      style={"color": TEAL,  "fontSize": "12px", "fontWeight": "600", "marginRight": "18px"}),
            html.Span("● Dados Sintéticos",
                      style={"color": AMBER, "fontSize": "12px", "fontWeight": "600"}),
        ]),
    ], style={
        "display": "flex",
        "justifyContent": "space-between",
        "alignItems": "center",
        "padding": "22px 24px",
        "background": SURF,
        "border": f"1px solid {BORDER}",
        "borderRadius": "12px",
        "marginBottom": "20px",
    }),

    # Insights fixos (calculados ao iniciar)
    html.Div([
        insight_card(
            f"Em 30 anos, o IDH do Brasil cresceu {_IDH_CRESC:.1f}% — de {_IDH_1991:.3f} em 1991 "
            f"para {_IDH_2021:.3f} em 2021, passando de desenvolvimento médio para alto.",
            TEAL, "📈"
        ),
        insight_card(_covid_insight, ROSE, "⚠️") if _covid_insight else html.Div(),
        insight_card(
            f"Mulheres vivem em média {_GAP_VIDA:.1f} anos a mais que homens ({_VIDA_FEM:.1f} vs "
            f"{_VIDA_MASC:.1f} anos), mas apresentam IDH inferior — reflexo de desigualdade "
            f"econômica e de mercado de trabalho.",
            PURPLE, "♀"
        ),
    ], style={"marginBottom": "4px"}),

    # Filtro
    filter_bar([
        filter_group("Período:", year_range_picker("home-slider", ANO_MIN, ANO_MAX)),
    ]),

    # KPIs
    kpi_row([
        kpi_card("IDH Inicial",          "home-kpi-start",  MUTED,  ""),
        kpi_card("IDH Final",            "home-kpi-end",    TEAL,   ""),
        kpi_card("Crescimento",          "home-kpi-var",    GREEN,  ""),
        kpi_card("Exp. de Vida Máx.",    "home-kpi-vida",   GREEN,  ""),
        kpi_card("Anos de Escola Máx.",  "home-kpi-escola", PURPLE, ""),
        kpi_card("Registros Sintéticos", "home-kpi-fake",   AMBER,  ""),
    ]),

    # Gráfico hero
    chart_card([
        dcc.Graph(id="home-hero", config={"displayModeBar": False})
    ], extra={"marginBottom": "18px"}),

    # Painel inferior
    html.Div([
        chart_card([
            html.Div([
                html.H4("O que é o IDH?", style={
                    "color": TEXT, "margin": "0 0 10px",
                    "fontSize": "14px", "fontWeight": "700",
                }),
                html.P([
                    "O ", html.Strong("Índice de Desenvolvimento Humano"),
                    " é um indicador composto criado pelo PNUD que mede o "
                    "progresso de um país em três dimensões: ",
                    html.Strong("saúde"), " (expectativa de vida), ",
                    html.Strong("educação"), " (anos de escolaridade) e ",
                    html.Strong("renda"), " (RNB per capita). "
                    "Varia de 0 a 1 — quanto maior, melhor."
                ], style={"color": MUTED, "fontSize": "13px",
                          "lineHeight": "1.75", "margin": "0 0 14px"}),
                html.Hr(style={"borderColor": BORDER, "margin": "14px 0"}),
                html.Div([
                    html.Div([
                        html.Span("< 0.550", style={"color": ROSE, "fontWeight": "700", "fontSize": "13px"}),
                        html.Span("  Baixo", style={"color": MUTED, "fontSize": "12px"}),
                    ], style={"marginBottom": "6px"}),
                    html.Div([
                        html.Span("0.550–0.699", style={"color": AMBER, "fontWeight": "700", "fontSize": "13px"}),
                        html.Span("  Médio", style={"color": MUTED, "fontSize": "12px"}),
                    ], style={"marginBottom": "6px"}),
                    html.Div([
                        html.Span("0.700–0.799", style={"color": TEAL, "fontWeight": "700", "fontSize": "13px"}),
                        html.Span("  Alto", style={"color": MUTED, "fontSize": "12px"}),
                    ], style={"marginBottom": "6px"}),
                    html.Div([
                        html.Span("> 0.800", style={"color": GREEN, "fontWeight": "700", "fontSize": "13px"}),
                        html.Span("  Muito Alto", style={"color": MUTED, "fontSize": "12px"}),
                    ]),
                ]),
            ], style={"padding": "20px"}),
        ], extra={"flex": "1"}),

        chart_card([
            html.Div([
                html.H4("Resumo do Período Selecionado", style={
                    "color": TEXT, "margin": "0 0 14px",
                    "fontSize": "14px", "fontWeight": "700",
                }),
                html.Div(id="home-resumo"),
                html.Div([
                    html.Span("Fonte: PNUD Brasil · Relatório de Desenvolvimento Humano 2021/22",
                              style={"color": MUTED, "fontSize": "11px"}),
                ], style={"marginTop": "16px", "paddingTop": "12px",
                          "borderTop": f"1px solid {BORDER}"}),
            ], style={"padding": "20px"}),
        ], extra={"flex": "1"}),
    ], style={"display": "flex", "gap": "14px"}),

], style={"padding": "24px"})


# ══════════════════════════════════════════════════════════════════════════════
#  PÁGINA 2 — IDH GERAL
# ══════════════════════════════════════════════════════════════════════════════
page_geral = html.Div([
    page_title(
        "30 anos de progresso — e um retrocesso",
        "O Brasil saiu do desenvolvimento médio em 1991 e atingiu o alto desenvolvimento em 2006, "
        "mas a pandemia de COVID-19 em 2020 reverteu ganhos acumulados em quase uma década."
    ),

    insight_card(
        "O IDH brasileiro cresceu de forma contínua por 28 anos (1991–2019). "
        "Em 2020, registrou a maior queda anual da série histórica: −0,008 pontos. "
        "Em 2021, ainda não havia recuperado o patamar pré-pandemia.",
        ROSE, "⚠️"
    ),

    filter_bar([
        filter_group("Período:", year_range_picker("geral-slider", ANO_MIN, ANO_MAX)),
        filter_group("Indicador:", styled_dd([
            {"label": "IDH Geral",           "value": "idh"},
            {"label": "Expectativa de Vida",  "value": "expectativa_de_vida"},
            {"label": "Anos de Escola",       "value": "expectativa_de_anos_escola"},
        ], "idh", "geral-indicador", "210px")),
        filter_group("Visualização:", styled_dd([
            {"label": "Linha",  "value": "linha"},
            {"label": "Área",   "value": "area"},
            {"label": "Barras", "value": "barras"},
        ], "linha", "geral-tipo", "130px")),
    ]),

    kpi_row([
        kpi_card("Valor Inicial", "geral-kpi-ini", MUTED),
        kpi_card("Valor Final",   "geral-kpi-fim", TEAL),
        kpi_card("Variação",      "geral-kpi-var", GREEN),
        kpi_card("Mínimo",        "geral-kpi-min", ROSE),
        kpi_card("Máximo",        "geral-kpi-max", AMBER),
    ]),

    chart_card([dcc.Graph(id="geral-main", config={"displayModeBar": False})],
               extra={"marginBottom": "16px"}),

    html.Div([
        chart_card([dcc.Graph(id="geral-vida",   config={"displayModeBar": False})],
                   extra={"flex": "1"}),
        chart_card([dcc.Graph(id="geral-escola", config={"displayModeBar": False})],
                   extra={"flex": "1"}),
    ], style={"display": "flex", "gap": "14px", "marginBottom": "16px"}),

    chart_card([
        html.Div([
            html.H4("Série Histórica Completa", style={
                "color": TEXT, "margin": "0 0 14px",
                "fontSize": "13px", "fontWeight": "600",
                "textTransform": "uppercase", "letterSpacing": "0.5px",
            }),
            html.Div(id="geral-tabela",
                     style={"maxHeight": "260px", "overflowY": "auto"}),
        ], style={"padding": "18px 20px"}),
    ]),

], style={"padding": "24px"})


# ══════════════════════════════════════════════════════════════════════════════
#  PÁGINA 3 — GÊNEROS
# ══════════════════════════════════════════════════════════════════════════════
page_generos = html.Div([
    page_title(
        "Mulheres vivem mais, mas desenvolvem menos",
        "Apesar de liderarem em expectativa de vida e anos de escolaridade, as mulheres brasileiras "
        "apresentam IDH inferior ao masculino — evidência da desigualdade econômica estrutural."
    ),

    insight_card(
        f"Em 2021, o IDH feminino foi 0,750 contra 0,755 masculino. "
        f"A diferença parece pequena, mas reflete uma desigualdade "
        f"persistente na dimensão de renda que não foi eliminada em 20 anos de dados.",
        PURPLE, "♀"
    ),
    insight_card(
        f"A expectativa de vida feminina supera a masculina em {_GAP_VIDA:.1f} anos. "
        f"Esse gap biológico e comportamental é consistente em toda a série histórica "
        f"e tende a se manter mesmo com melhorias gerais no sistema de saúde.",
        TEAL, "📊"
    ),

    filter_bar([
        filter_group("Período:", year_range_picker("gen-slider", ANOS_GENERO_MIN, ANO_MAX)),
        filter_group("Séries:", html.Div([
            html.Button("Feminino",  id="btn-gen-fem",  n_clicks=0),
            html.Button("Masculino", id="btn-gen-masc", n_clicks=0),
            html.Button("Geral",     id="btn-gen-geral", n_clicks=0),
            dcc.Store(id="gen-series", data=["fem", "masc", "geral"]),
        ], style={"display": "flex", "gap": "6px"})),
        filter_group("Indicador:", styled_dd([
            {"label": "IDH",                 "value": "idh"},
            {"label": "Expectativa de Vida",  "value": "vida"},
            {"label": "Anos de Escola",       "value": "escola"},
        ], "idh", "gen-indicador", "210px")),
    ]),

    kpi_row([
        kpi_card("IDH Feminino (fim)",   "gen-kpi-fem",   PURPLE),
        kpi_card("IDH Masculino (fim)",  "gen-kpi-masc",  TEAL),
        kpi_card("Gap (Masc − Fem)",     "gen-kpi-gap",   AMBER),
        kpi_card("Vida Feminina (fim)",  "gen-kpi-vfem",  PURPLE),
        kpi_card("Vida Masculina (fim)", "gen-kpi-vmasc", TEAL),
    ]),

    chart_card([dcc.Graph(id="gen-linhas", config={"displayModeBar": False})],
               extra={"marginBottom": "16px"}),

    html.Div([
        chart_card([dcc.Graph(id="gen-gap",    config={"displayModeBar": False})],
                   extra={"flex": "1"}),
        chart_card([dcc.Graph(id="gen-escola", config={"displayModeBar": False})],
                   extra={"flex": "1"}),
    ], style={"display": "flex", "gap": "14px"}),

], style={"padding": "24px"})


# ══════════════════════════════════════════════════════════════════════════════
#  PÁGINA 4 — CENÁRIOS
# ══════════════════════════════════════════════════════════════════════════════
page_cenarios = html.Div([
    page_title(
        "Dados reais vs. dados sintéticos — o quão fiel é a simulação?",
        "O dataset sintético (1.000 registros gerados via SVD) é comparado aos dados reais do PNUD. "
        "Quanto menor a diferença entre eles, mais o modelo captura a realidade histórica."
    ),

    insight_card(
        "Dados sintéticos gerados por SVD (Decomposição em Valores Singulares) preservam "
        "a estrutura estatística do dataset original. São usados para ampliar amostras em "
        "modelos preditivos sem violar privacidade ou escassez de dados históricos.",
        BLUE, "🔬"
    ),

    filter_bar([
        filter_group("Período:", year_range_picker("cen-slider", ANO_MIN, ANO_MAX)),
        filter_group("Agregação:", styled_dd([
            {"label": "Média",   "value": "mean"},
            {"label": "Mediana", "value": "median"},
            {"label": "Mínimo",  "value": "min"},
            {"label": "Máximo",  "value": "max"},
        ], "mean", "cen-agr", "140px")),
        filter_group("Banda (σ):", styled_dd([
            {"label": "0.5σ", "value": 0.5},
            {"label": "1.0σ", "value": 1.0},
            {"label": "1.5σ", "value": 1.5},
            {"label": "2.0σ", "value": 2.0},
        ], 1.0, "cen-sigma", "100px")),
        filter_group("", html.Div([
            html.Button("Incerteza", id="btn-cen-banda", n_clicks=0),
            dcc.Store(id="cen-banda", data=["show"]),
        ])),
    ]),

    kpi_row([
        kpi_card("IDH Real (média)",     "cen-kpi-real", TEAL),
        kpi_card("IDH Sint. (agr.)",     "cen-kpi-fake", AMBER),
        kpi_card("Diferença absoluta",   "cen-kpi-diff", ROSE),
        kpi_card("Desvio Padrão Sint.",  "cen-kpi-std",  PURPLE),
        kpi_card("Registros no período", "cen-kpi-n",    MUTED),
    ]),

    chart_card([dcc.Graph(id="cen-compare", config={"displayModeBar": False})],
               extra={"marginBottom": "16px"}),

    html.Div([
        chart_card([dcc.Graph(id="cen-scatter", config={"displayModeBar": False})],
                   extra={"flex": "1"}),
        chart_card([dcc.Graph(id="cen-vida",    config={"displayModeBar": False})],
                   extra={"flex": "1"}),
    ], style={"display": "flex", "gap": "14px", "marginBottom": "16px"}),

    chart_card([dcc.Graph(id="cen-box", config={"displayModeBar": False})]),

], style={"padding": "24px"})


# ══════════════════════════════════════════════════════════════════════════════
#  APP + LAYOUT GERAL
# ══════════════════════════════════════════════════════════════════════════════
NAV_ITEMS = [
    {"id": "home",     "label": "Panorama",   "icon": "◈"},
    {"id": "geral",    "label": "IDH Geral",  "icon": "◈"},
    {"id": "generos",  "label": "Gêneros",    "icon": "◈"},
    {"id": "cenarios", "label": "Cenários",   "icon": "◈"},
]

PAGES = [page_home, page_geral, page_generos, page_cenarios]

app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    title="IDH Brasil · Dashboard Analítico",
)

# CSS global — força cores explícitas para evitar conflito com Chrome dark mode
app.index_string = (
    "<!DOCTYPE html>\n<html>\n<head>\n{%metas%}\n<title>{%title%}</title>\n"
    "{%favicon%}\n{%css%}\n"
    "<link href='https://fonts.googleapis.com/css2?"
    "family=Inter:wght@400;500;600;700;800&display=swap' rel='stylesheet'>\n"
    "<style>\n"
    # ── Reset e base ─────────────────────────────────────────────────────────
    "*, *::before, *::after { box-sizing: border-box; }\n"
    "html, body {\n"
    "  background: " + BG + ";\n"
    "  color: " + TEXT + ";\n"
    "  font-family: " + FONT + ";\n"
    "  margin: 0; padding: 0;\n"
    "  /* Força modo claro para controles nativos (input, select, scrollbar) */\n"
    "  color-scheme: dark;\n"
    "}\n"
    # ── Scrollbar ────────────────────────────────────────────────────────────
    "::-webkit-scrollbar { width: 5px; height: 5px; }\n"
    "::-webkit-scrollbar-track { background: " + BG + "; }\n"
    "::-webkit-scrollbar-thumb { background: " + BORDER + "; border-radius: 3px; }\n"
    "::-webkit-scrollbar-thumb:hover { background: " + MUTED + "; }\n"
    # ── Dropdown — seletores universais (funciona em qualquer versão do Dash) ─
    # Cobre: React-Select v1 (.Select-*), v2/v3 (.Select__*), Dash 4 (div[class*=container])
    "[class*='dropdown'] input, [class*='Dropdown'] input { color: #111827 !important; }\n"
    # Controle (caixa principal visível)
    "[class*='control'], [class*='Control'] {\n"
    "  background-color: #ffffff !important;\n"
    "  border-color: " + BORDER + " !important;\n"
    "  border-radius: 7px !important;\n"
    "  min-height: 34px !important;\n"
    "  cursor: pointer !important;\n"
    "  box-shadow: none !important;\n"
    "}\n"
    # Valor selecionado
    "[class*='singleValue'], [class*='single-value'],\n"
    "[class*='value-label'], .Select-value-label {\n"
    "  color: #111827 !important;\n"
    "  font-size: 13px !important;\n"
    "}\n"
    # Placeholder
    "[class*='placeholder'], .Select-placeholder {\n"
    "  color: #6b7280 !important;\n"
    "}\n"
    # Input de busca interno
    "[class*='Input'] input { color: #111827 !important; }\n"
    # Menu (lista de opções)
    "[class*='menu'], [class*='Menu'],\n"
    ".Select-menu-outer, .VirtualizedSelectFocusedOption {\n"
    "  background-color: #ffffff !important;\n"
    "  border: 1px solid " + BORDER + " !important;\n"
    "  border-radius: 8px !important;\n"
    "  z-index: 9999 !important;\n"
    "  box-shadow: 0 8px 24px rgba(0,0,0,0.3) !important;\n"
    "}\n"
    # Opções individuais
    "[class*='option'], .Select-option {\n"
    "  background-color: #ffffff !important;\n"
    "  color: #111827 !important;\n"
    "  font-size: 13px !important;\n"
    "  cursor: pointer !important;\n"
    "}\n"
    "[class*='option']:hover, [class*='option--is-focused'],\n"
    ".Select-option.is-focused {\n"
    "  background-color: #eff6ff !important;\n"
    "  color: #1d4ed8 !important;\n"
    "}\n"
    "[class*='option--is-selected'], .Select-option.is-selected {\n"
    "  background-color: #dbeafe !important;\n"
    "  color: #1e40af !important;\n"
    "  font-weight: 600 !important;\n"
    "}\n"
    # Seta/indicador
    "[class*='indicatorContainer'] svg, [class*='indicator'] svg {\n"
    "  color: #6b7280 !important;\n"
    "}\n"
    "[class*='indicatorSeparator'] { background-color: " + BORDER + " !important; }\n"
    ".Select-arrow { border-top-color: #6b7280 !important; }\n"
    # ── Slider ───────────────────────────────────────────────────────────────
    ".rc-slider-rail { background: " + BORDER + " !important; }\n"
    ".rc-slider-track { background: " + BLUE + " !important; }\n"
    ".rc-slider-handle {\n"
    "  border-color: " + BLUE + " !important;\n"
    "  background: " + SURF + " !important;\n"
    "  box-shadow: 0 0 0 2px " + BLUE + " !important;\n"
    "  opacity: 1 !important;\n"
    "}\n"
    ".rc-slider-handle:hover { border-color: " + TEAL + " !important; }\n"
    # Esconde os pontos de marca que ficam "voando" como bolinhas
    ".rc-slider-dot { display: none !important; }\n"
    ".rc-slider-mark-text { color: " + MUTED + " !important; font-size: 10px !important; }\n"
    # Tooltip do slider (hover)
    ".rc-slider-tooltip-inner {\n"
    "  background: " + SURF2 + " !important;\n"
    "  color: " + TEXT + " !important;\n"
    "  border: 1px solid " + BORDER + " !important;\n"
    "  font-size: 11px !important;\n"
    "  padding: 3px 8px !important;\n"
    "}\n"
    ".rc-slider-tooltip { z-index: 9999 !important; }\n"
    # ── Botões toggle (sem nenhum elemento nativo do browser) ────────────────
    ".toggle-btn {\n"
    "  padding: 5px 14px;\n"
    "  border-radius: 6px;\n"
    "  border: 1px solid " + BORDER + ";\n"
    "  background: " + SURF2 + ";\n"
    "  color: " + MUTED + ";\n"
    "  font-size: 12px;\n"
    "  font-weight: 500;\n"
    "  font-family: " + FONT + ";\n"
    "  cursor: pointer;\n"
    "  transition: all 0.15s ease;\n"
    "  white-space: nowrap;\n"
    "  outline: none;\n"
    "}\n"
    ".toggle-btn:hover {\n"
    "  border-color: " + BLUE + ";\n"
    "  color: " + TEXT + ";\n"
    "}\n"
    ".toggle-btn-on {\n"
    "  background: " + rgba(BLUE, 0.15) + " !important;\n"
    "  border-color: " + BLUE + " !important;\n"
    "  color: " + TEXT + " !important;\n"
    "  font-weight: 600 !important;\n"
    "}\n"
    # ── Forçar cor de texto em TODOS os elementos (anula Chrome dark mode) ──
    "p, span, h1, h2, h3, h4, h5, h6, div, td, th, li, label {\n"
    "  color: inherit;\n"
    "}\n"
    # Insight cards — texto explicitamente claro
    ".insight-text { color: " + TEXT + " !important; }\n"
    # ── Nav button hover ─────────────────────────────────────────────────────
    ".nav-btn:hover {\n"
    "  background: " + rgba(BLUE, 0.1) + " !important;\n"
    "  color: " + TEXT + " !important;\n"
    "}\n"
    # ── Animação de transição de página ──────────────────────────────────────
    "@keyframes pgIn {\n"
    "  from { opacity: 0; transform: translateY(6px); }\n"
    "  to   { opacity: 1; transform: translateY(0); }\n"
    "}\n"
    "#page-content > div { animation: pgIn 0.2s ease; }\n"
    "</style>\n"
    "</head>\n<body>\n{%app_entry%}\n"
    "<footer>{%config%}{%scripts%}{%renderer%}</footer>\n</body>\n</html>\n"
)

app.layout = html.Div([
    dcc.Store(id="active-page", data="home"),

    # ── Sidebar ───────────────────────────────────────────────────────────────
    html.Div([

        # Logo
        html.Div([
            html.Div("IDH", style={
                "fontSize": "22px", "fontWeight": "800",
                "color": TEAL, "letterSpacing": "-0.5px",
                "display": "inline",
            }),
            html.Div("Brasil", style={
                "fontSize": "22px", "fontWeight": "800",
                "color": TEXT, "letterSpacing": "-0.5px",
                "display": "inline", "marginLeft": "5px",
            }),
            html.Div("Dashboard Analítico", style={
                "color": MUTED, "fontSize": "10px",
                "textTransform": "uppercase",
                "letterSpacing": "1.5px", "marginTop": "4px",
            }),
        ], style={
            "padding": "22px 18px 18px",
            "borderBottom": f"1px solid {BORDER}",
        }),

        # Separador de seção
        html.Div("NAVEGAÇÃO", style={
            "color": MUTED, "fontSize": "9px",
            "textTransform": "uppercase", "letterSpacing": "1.5px",
            "padding": "14px 18px 6px", "fontWeight": "600",
        }),

        # Botões de navegação
        html.Div([
            html.Button(
                html.Div([
                    html.Span("▸ ", style={
                        "fontSize": "10px", "color": TEAL,
                        "marginRight": "2px",
                    }),
                    html.Span(item["label"], style={
                        "fontSize": "13px", "fontWeight": "500",
                    }),
                ], style={"display": "flex", "alignItems": "center"}),
                id=f"nav-{item['id']}",
                n_clicks=0,
                className="nav-btn",
                style={
                    "width": "100%",
                    "textAlign": "left",
                    "background": "transparent",
                    "border": "none",
                    "color": MUTED,
                    "padding": "10px 14px",
                    "cursor": "pointer",
                    "borderRadius": "8px",
                    "marginBottom": "2px",
                    "fontFamily": FONT,
                    "transition": "all 0.15s ease",
                    "display": "block",
                },
            )
            for item in NAV_ITEMS
        ], style={"padding": "0 8px"}),

        # Footer da sidebar — posicionado com padding, não marginTop auto
        html.Div([
            html.Div(style={
                "width": "24px", "height": "2px",
                "background": TEAL,
                "borderRadius": "1px", "marginBottom": "10px",
            }),
            html.Div("Fonte dos dados", style={
                "color": MUTED, "fontSize": "9px",
                "textTransform": "uppercase", "letterSpacing": "1px",
                "marginBottom": "4px",
            }),
            html.P("PNUD Brasil · Relatório IDH 2021/22",
                   style={"color": MUTED, "fontSize": "11px", "margin": "0"}),
            html.P("Série histórica 1991–2021",
                   style={"color": MUTED, "fontSize": "11px", "margin": "3px 0 0"}),
        ], style={
            "padding": "16px 18px",
            "borderTop": f"1px solid {BORDER}",
            "marginTop": "24px",    # padding fixo, não auto
        }),

    ], style={
        "width": "200px",
        "minWidth": "200px",
        "background": SURF,
        "borderRight": f"1px solid {BORDER}",
        "height": "100vh",
        "position": "fixed",
        "left": "0", "top": "0",
        "zIndex": "100",
        "overflowY": "auto",
        "display": "flex",
        "flexDirection": "column",
        "boxShadow": f"2px 0 20px {rgba(BG, 0.9)}",
    }),

    # ── Conteúdo ──────────────────────────────────────────────────────────────
    html.Div(id="page-content", style={
        "marginLeft": "200px",
        "minHeight": "100vh",
        "background": BG,
        "overflowY": "auto",
    }),

], style={
    "display": "flex",
    "background": BG,
    "fontFamily": FONT,
    "color": TEXT,
    "minHeight": "100vh",
})


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
    ctx = callback_context
    if ctx.triggered and ctx.triggered[0]["prop_id"] != "active-page.data":
        active = ctx.triggered[0]["prop_id"].split(".")[0].replace("nav-", "")

    pages_map = {i["id"]: p for i, p in zip(NAV_ITEMS, PAGES)}

    def nav_style(iid):
        on = iid == active
        return {
            "width": "100%", "textAlign": "left",
            "background": rgba(BLUE, 0.12) if on else "transparent",
            "border": "none",
            "color": TEXT if on else MUTED,
            "padding": "10px 14px",
            "cursor": "pointer", "borderRadius": "8px",
            "marginBottom": "2px", "fontFamily": FONT,
            "fontWeight": "600" if on else "500",
            "fontSize": "13px",
            "borderLeft": f"3px solid {TEAL}" if on else f"3px solid transparent",
            "transition": "all 0.15s ease",
            "display": "block",
        }

    return (
        pages_map.get(active, page_home),
        active,
        *[nav_style(i["id"]) for i in NAV_ITEMS],
    )


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
    Input("home-slider-start", "value"),
    Input("home-slider-end",   "value"),
)
def cb_home(a, b):
    a = a or ANO_MIN
    b = b or ANO_MAX
    if a > b:
        a, b = b, a
    dr = df_real[(df_real["ano_referencia"] >= a) & (df_real["ano_referencia"] <= b)].copy()
    df = df_fake[(df_fake["ano_referencia"] >= a) & (df_fake["ano_referencia"] <= b)].copy()

    # NaN-safe
    idh_clean = dr["idh"].dropna()
    i0  = idh_clean.iloc[0]  if len(idh_clean) > 0 else None
    i1  = idh_clean.iloc[-1] if len(idh_clean) > 0 else None
    var = ((i1 / i0) - 1) * 100 if (i0 and i1 and i0 != 0) else None

    fake_agg = df.groupby("ano_referencia")["idh"].mean().dropna()
    fake_std = df.groupby("ano_referencia")["idh"].std().fillna(0)

    fig = go.Figure()

    # Banda sintética
    if len(fake_agg) >= 2:
        anos_f = fake_agg.index.tolist()
        upper  = (fake_agg + fake_std).tolist()
        lower  = (fake_agg - fake_std).tolist()
        fig.add_trace(go.Scatter(
            x=anos_f + anos_f[::-1],
            y=upper + lower[::-1],
            fill="toself",
            fillcolor=rgba(AMBER, 0.10),
            line=dict(width=0),
            hoverinfo="skip",
            showlegend=True,
            name="Banda ±1σ (sint.)",
        ))
        fig.add_trace(go.Scatter(
            x=fake_agg.index, y=fake_agg.values,
            mode="lines", name="IDH Sintético (média)",
            line=dict(color=AMBER, width=2, dash="dot"),
            hovertemplate="<b>%{x}</b><br>IDH Sint.: %{y:.3f}<extra></extra>",
        ))

    fig.add_trace(go.Scatter(
        x=dr["ano_referencia"], y=dr["idh"],
        mode="lines+markers", name="IDH Real (PNUD)",
        line=dict(color=TEAL, width=3),
        marker=dict(size=6, color=TEAL, line=dict(width=2, color=BG)),
        fill="tozeroy", fillcolor=rgba(TEAL, 0.05),
        hovertemplate="<b>%{x}</b><br>IDH Real: %{y:.3f}<extra></extra>",
    ))

    # Anotação: queda COVID
    if 2020 in dr["ano_referencia"].values:
        v20 = dr.loc[dr["ano_referencia"] == 2020, "idh"].values[0]
        fig.add_annotation(
            x=2020, y=v20,
            text="↓ COVID-19",
            showarrow=True, arrowhead=2,
            arrowcolor=ROSE, arrowwidth=1.5,
            font=dict(color=ROSE, size=11, family=FONT),
            bgcolor=SURF, bordercolor=ROSE, borderwidth=1,
            ax=30, ay=-36,
        )

    # Anotação: pico máximo
    if len(idh_clean) > 0:
        idx_max = dr["idh"].idxmax()
        row_max = dr.loc[idx_max]
        if row_max["ano_referencia"] != 2020:
            fig.add_annotation(
                x=row_max["ano_referencia"], y=row_max["idh"],
                text=f"Pico: {row_max['idh']:.3f}",
                showarrow=True, arrowhead=2,
                arrowcolor=GREEN, arrowwidth=1.5,
                font=dict(color=GREEN, size=11, family=FONT),
                bgcolor=SURF, bordercolor=GREEN, borderwidth=1,
                ax=0, ay=-40,
            )

    fig.update_layout(**base_layout(
        title=f"<b>Evolução do IDH Brasileiro</b> · {a}–{b}",
        height=310,
    ))

    # Tabela de resumo
    v_vida_ini = _safe_val(dr["expectativa_de_vida"], 0, "{:.1f} anos")
    v_vida_fim = _safe_val(dr["expectativa_de_vida"], -1, "{:.1f} anos")
    v_esc_ini  = _safe_val(dr["expectativa_de_anos_escola"], 0, "{:.1f} anos")
    v_esc_fim  = _safe_val(dr["expectativa_de_anos_escola"], -1, "{:.1f} anos")

    rows_data = [
        ("Período selecionado",     f"{a} – {b}"),
        ("Variação IDH",            f"+{var:.1f}%" if var is not None else "—"),
        ("Exp. Vida · início",      v_vida_ini),
        ("Exp. Vida · fim",         v_vida_fim),
        ("Anos de Escola · início", v_esc_ini),
        ("Anos de Escola · fim",    v_esc_fim),
        ("Registros sintéticos",    f"{len(df):,}".replace(",", ".")),
    ]

    resumo = html.Table([
        html.Tbody([
            html.Tr([
                html.Td(r, style={
                    "color": MUTED, "padding": "7px 4px 7px 0",
                    "fontSize": "12px", "whiteSpace": "nowrap",
                    "borderTop": f"1px solid {BORDER}",
                }),
                html.Td(v, style={
                    "color": TEXT, "padding": "7px 0 7px 12px",
                    "fontSize": "13px", "textAlign": "right",
                    "fontWeight": "600",
                    "borderTop": f"1px solid {BORDER}",
                }),
            ]) for r, v in rows_data
        ]),
    ], style={"width": "100%", "borderCollapse": "collapse"})

    return (
        f"{i0:.3f}" if i0 is not None else "—",
        f"{i1:.3f}" if i1 is not None else "—",
        f"+{var:.1f}%" if var is not None else "—",
        _safe_val(dr["expectativa_de_vida"], -1, "{:.1f} anos"),
        _safe_val(dr["expectativa_de_anos_escola"], -1, "{:.1f} anos"),
        f"{len(df):,}".replace(",", "."),
        fig,
        resumo,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  CALLBACKS — IDH GERAL
# ══════════════════════════════════════════════════════════════════════════════
_IND_CFG = {
    "idh": (
        "IDH Geral", "{:.3f}", TEAL,
        "O IDH consolida saúde, educação e renda em um único índice. "
        "A linha média ajuda a visualizar anos acima ou abaixo do desempenho histórico."
    ),
    "expectativa_de_vida": (
        "Expectativa de Vida (anos)", "{:.1f}", GREEN,
        "A expectativa de vida ao nascer reflete a qualidade dos serviços de saúde, "
        "saneamento e condições socioeconômicas do país."
    ),
    "expectativa_de_anos_escola": (
        "Anos Esperados de Escola", "{:.1f}", PURPLE,
        "Mede quantos anos de escolaridade uma criança que entra na escola hoje "
        "pode esperar receber ao longo da vida."
    ),
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
    Input("geral-slider-start", "value"),
    Input("geral-slider-end",   "value"),
    Input("geral-indicador",    "value"),
    Input("geral-tipo",         "value"),
)
def cb_geral(a, b, indicador, tipo):
    a = a or ANO_MIN
    b = b or ANO_MAX
    if a > b:
        a, b = b, a
    dr = df_real[(df_real["ano_referencia"] >= a) & (df_real["ano_referencia"] <= b)].copy()
    label, fmt, color, _ = _IND_CFG.get(indicador, _IND_CFG["idh"])
    col_clean = dr[indicador].dropna()

    ini = fmt.format(col_clean.iloc[0])  if len(col_clean) > 0 else "—"
    fim = fmt.format(col_clean.iloc[-1]) if len(col_clean) > 0 else "—"
    var_num = ((col_clean.iloc[-1] / col_clean.iloc[0]) - 1) * 100 if (len(col_clean) > 1 and col_clean.iloc[0]) else None
    var = f"{var_num:+.1f}%" if var_num is not None else "—"
    mn  = fmt.format(col_clean.min()) if len(col_clean) > 0 else "—"
    mx  = fmt.format(col_clean.max()) if len(col_clean) > 0 else "—"

    anos = dr["ano_referencia"]
    vals = dr[indicador].dropna()
    avg  = vals.mean() if len(vals) > 0 else 0

    # ── Gráfico principal ────────────────────────────────────────────────────
    fig_main = go.Figure()
    ht = f"<b>%{{x}}</b><br>{label}: %{{y}}<extra></extra>"

    if tipo == "linha":
        fig_main.add_trace(go.Scatter(
            x=anos, y=dr[indicador], mode="lines+markers",
            name=label, line=dict(color=color, width=3),
            marker=dict(size=6, color=color, line=dict(width=2, color=BG)),
            hovertemplate=ht,
        ))
        fig_main.add_hline(
            y=avg, line_color=rgba(MUTED, 0.5), line_width=1.5, line_dash="dot",
            annotation_text=f"Média: {fmt.format(avg)}",
            annotation_font=dict(color=MUTED, size=10),
            annotation_position="top right",
        )

    elif tipo == "area":
        fig_main.add_trace(go.Scatter(
            x=anos, y=dr[indicador], mode="lines", name=label,
            line=dict(color=color, width=2.5),
            fill="tozeroy", fillcolor=rgba(color, 0.08),
            hovertemplate=ht,
        ))

    elif tipo == "barras":
        bar_colors = [color if (not np.isnan(v) and v >= avg) else rgba(color, 0.35)
                      for v in dr[indicador]]
        fig_main.add_trace(go.Bar(
            x=anos, y=dr[indicador],
            marker_color=bar_colors,
            marker_line_color=BORDER, marker_line_width=0.5,
            name=label, hovertemplate=ht,
        ))
        fig_main.add_hline(
            y=avg, line_color=AMBER, line_width=1.5, line_dash="dot",
            annotation_text=f"Média: {fmt.format(avg)}",
            annotation_font=dict(color=AMBER, size=10),
            annotation_position="top right",
        )

    # Marca COVID se visível
    if 2020 in dr["ano_referencia"].values:
        v20 = dr.loc[dr["ano_referencia"] == 2020, indicador].values
        if len(v20) and not np.isnan(v20[0]):
            fig_main.add_annotation(
                x=2020, y=v20[0], text="↓ 2020",
                showarrow=True, arrowhead=2,
                arrowcolor=ROSE, font=dict(color=ROSE, size=10),
                bgcolor=SURF, bordercolor=ROSE, borderwidth=1,
                ax=30, ay=-32,
            )

    fig_main.update_layout(**base_layout(
        title=f"<b>{label}</b> · {a}–{b}", height=310,
    ))

    # ── Mini expectativa de vida ─────────────────────────────────────────────
    fig_vida = go.Figure()
    series_vida = [
        ("expectativa_de_vida",           "Geral",    TEAL,   "solid",  3),
        ("expectativa_de_vida_feminina",  "Feminina", PURPLE, "dash",   2),
        ("expectativa_de_vida_masculina", "Masculina",BLUE,   "dot",    2),
    ]
    for col_v, nome_v, cor_v, dash_v, w_v in series_vida:
        if col_v in dr.columns:
            fig_vida.add_trace(go.Scatter(
                x=dr["ano_referencia"], y=dr[col_v],
                mode="lines", name=nome_v,
                line=dict(color=cor_v, width=w_v, dash=dash_v),
                hovertemplate=f"<b>%{{x}}</b><br>{nome_v}: %{{y:.1f}} anos<extra></extra>",
            ))
    fig_vida.update_layout(**base_layout(
        title="<b>Expectativa de Vida</b> por gênero", height=260,
    ))

    # ── Mini anos de escola ──────────────────────────────────────────────────
    avg_esc = dr["expectativa_de_anos_escola"].dropna().mean() if len(dr) > 0 else 0
    bar_esc = [
        PURPLE if (not np.isnan(v) and v >= avg_esc) else rgba(PURPLE, 0.35)
        for v in dr["expectativa_de_anos_escola"]
    ]
    fig_esc = go.Figure()
    fig_esc.add_trace(go.Bar(
        x=dr["ano_referencia"], y=dr["expectativa_de_anos_escola"],
        marker_color=bar_esc, marker_line_color=BORDER, marker_line_width=0.5,
        name="Anos esperados",
        hovertemplate="<b>%{x}</b><br>Anos: %{y:.1f}<extra></extra>",
    ))
    fig_esc.update_layout(**base_layout(
        title="<b>Anos Esperados de Escola</b>", height=260,
    ))

    # ── Tabela ───────────────────────────────────────────────────────────────
    th_s = {
        "color": MUTED, "padding": "8px 14px",
        "fontSize": "10px", "textAlign": "right",
        "borderBottom": f"2px solid {BORDER}",
        "textTransform": "uppercase", "letterSpacing": "0.5px",
        "fontWeight": "600", "background": SURF2,
    }
    td_s = lambda c, fw="400": {
        "color": c, "padding": "7px 14px",
        "fontSize": "12px", "textAlign": "right",
        "fontWeight": fw, "borderTop": f"1px solid {BORDER}",
    }
    tabela = html.Table([
        html.Thead(html.Tr([
            html.Th(h, style=th_s)
            for h in ["Ano", "IDH", "Exp. Vida (anos)", "Anos de Escola"]
        ])),
        html.Tbody([
            html.Tr([
                html.Td(str(int(row["ano_referencia"])), style=td_s(MUTED)),
                html.Td(f"{row['idh']:.3f}" if not pd.isna(row['idh']) else "—",
                        style=td_s(TEAL, "700")),
                html.Td(f"{row['expectativa_de_vida']:.1f}" if not pd.isna(row['expectativa_de_vida']) else "—",
                        style=td_s(TEXT)),
                html.Td(f"{row['expectativa_de_anos_escola']:.1f}" if not pd.isna(row['expectativa_de_anos_escola']) else "—",
                        style=td_s(TEXT)),
            ]) for _, row in dr.iterrows()
        ]),
    ], style={"width": "100%", "borderCollapse": "collapse"})

    return ini, fim, var, mn, mx, fig_main, fig_vida, fig_esc, tabela


# ══════════════════════════════════════════════════════════════════════════════
#  CALLBACKS — BOTÕES TOGGLE
# ══════════════════════════════════════════════════════════════════════════════
_BTN_ON  = {"padding": "5px 14px", "borderRadius": "6px",
            "border": f"1px solid {BLUE}", "background": rgba(BLUE, 0.15),
            "color": TEXT, "fontSize": "12px", "fontWeight": "600",
            "fontFamily": FONT, "cursor": "pointer", "outline": "none",
            "transition": "all 0.15s ease", "whiteSpace": "nowrap"}
_BTN_OFF = {"padding": "5px 14px", "borderRadius": "6px",
            "border": f"1px solid {BORDER}", "background": SURF2,
            "color": MUTED, "fontSize": "12px", "fontWeight": "500",
            "fontFamily": FONT, "cursor": "pointer", "outline": "none",
            "transition": "all 0.15s ease", "whiteSpace": "nowrap"}

@app.callback(
    Output("gen-series",    "data"),
    Output("btn-gen-fem",   "style"),
    Output("btn-gen-masc",  "style"),
    Output("btn-gen-geral", "style"),
    Input("btn-gen-fem",    "n_clicks"),
    Input("btn-gen-masc",   "n_clicks"),
    Input("btn-gen-geral",  "n_clicks"),
    Input("gen-series",     "data"),
    prevent_initial_call=False,
)
def toggle_gen_series(nf, nm, ng, current):
    current = current or ["fem", "masc", "geral"]
    ctx = callback_context
    if ctx.triggered and ctx.triggered[0]["prop_id"] != "gen-series.data":
        key = ctx.triggered[0]["prop_id"].split(".")[0].replace("btn-gen-", "")
        mapping = {"fem": "fem", "masc": "masc", "geral": "geral"}
        val = mapping.get(key)
        if val:
            if val in current:
                # Não remove se for o último ativo
                if len(current) > 1:
                    current = [v for v in current if v != val]
            else:
                current = current + [val]
    s = lambda v: _BTN_ON if v in current else _BTN_OFF
    return current, s("fem"), s("masc"), s("geral")


@app.callback(
    Output("cen-banda",     "data"),
    Output("btn-cen-banda", "style"),
    Input("btn-cen-banda",  "n_clicks"),
    Input("cen-banda",      "data"),
    prevent_initial_call=False,
)
def toggle_cen_banda(n, current):
    current = current if current is not None else ["show"]
    ctx = callback_context
    if ctx.triggered and ctx.triggered[0]["prop_id"] == "btn-cen-banda.n_clicks" and n:
        current = [] if "show" in current else ["show"]
    style = _BTN_ON if "show" in current else _BTN_OFF
    return current, style


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
    Input("gen-slider-start", "value"),
    Input("gen-slider-end",   "value"),
    Input("gen-series",       "data"),
    Input("gen-indicador",    "value"),
)
def cb_generos(a, b, series, indicador):
    a = a or ANOS_GENERO_MIN
    b = b or ANO_MAX
    if a > b:
        a, b = b, a
    dr = df_real[
        (df_real["ano_referencia"] >= a) &
        (df_real["ano_referencia"] <= b) &
        (df_real["idh_feminino"] > 0)    # anos sem dado de gênero = 0
    ].copy()

    kpi_fem  = _safe_val(dr["idh_feminino"],  -1, "{:.3f}")
    kpi_masc = _safe_val(dr["idh_masculino"], -1, "{:.3f}")

    try:
        gap_v   = dr["idh_masculino"].dropna().iloc[-1] - dr["idh_feminino"].dropna().iloc[-1]
        kpi_gap = f"{gap_v:+.4f}"
    except Exception:
        kpi_gap = "—"

    kpi_vf  = _safe_val(dr["expectativa_de_vida_feminina"],  -1, "{:.1f} anos")
    kpi_vm  = _safe_val(dr["expectativa_de_vida_masculina"], -1, "{:.1f} anos")

    _cols = {
        "idh":    ("idh_feminino",                       "idh_masculino",                      "idh"),
        "vida":   ("expectativa_de_vida_feminina",        "expectativa_de_vida_masculina",       "expectativa_de_vida"),
        "escola": ("expectativa_de_anos_escola_feminina", "expectativa_de_anos_escola_masculina","expectativa_de_anos_escola"),
    }
    _labs = {
        "idh":    ("IDH Feminino",  "IDH Masculino",  "IDH Geral"),
        "vida":   ("Vida Feminina", "Vida Masculina", "Vida Geral"),
        "escola": ("Escola Fem.",   "Escola Masc.",   "Escola Geral"),
    }
    col_f, col_m, col_g = _cols.get(indicador, _cols["idh"])
    lab_f, lab_m, lab_g = _labs.get(indicador, _labs["idh"])

    series = series or []
    fig_lin = go.Figure()
    if "fem" in series and col_f in dr.columns:
        fig_lin.add_trace(go.Scatter(
            x=dr["ano_referencia"], y=dr[col_f], name=lab_f,
            mode="lines+markers", line=dict(color=PURPLE, width=3),
            marker=dict(size=6, color=PURPLE, line=dict(width=2, color=BG)),
            hovertemplate=f"<b>%{{x}}</b><br>{lab_f}: %{{y:.3f}}<extra></extra>",
        ))
    if "masc" in series and col_m in dr.columns:
        fig_lin.add_trace(go.Scatter(
            x=dr["ano_referencia"], y=dr[col_m], name=lab_m,
            mode="lines+markers", line=dict(color=TEAL, width=3),
            marker=dict(size=6, color=TEAL, line=dict(width=2, color=BG)),
            hovertemplate=f"<b>%{{x}}</b><br>{lab_m}: %{{y:.3f}}<extra></extra>",
        ))
    if "geral" in series and col_g in dr.columns:
        fig_lin.add_trace(go.Scatter(
            x=dr["ano_referencia"], y=dr[col_g], name=lab_g,
            mode="lines", line=dict(color=rgba(MUTED, 0.8), width=1.5, dash="dot"),
            hovertemplate=f"<b>%{{x}}</b><br>{lab_g}: %{{y:.3f}}<extra></extra>",
        ))

    ind_label = {"idh": "IDH", "vida": "Expectativa de Vida", "escola": "Anos de Escola"}
    fig_lin.update_layout(**base_layout(
        title=f"<b>{ind_label.get(indicador, indicador)} por Gênero</b> · {a}–{b}",
        height=310,
    ))

    # Gap IDH
    gap = dr["idh_masculino"] - dr["idh_feminino"]
    fig_gap = go.Figure()
    fig_gap.add_trace(go.Bar(
        x=dr["ano_referencia"], y=gap,
        marker_color=[AMBER if v > 0 else GREEN for v in gap.fillna(0)],
        marker_line_color=BORDER, marker_line_width=0.5,
        name="Gap (Masc − Fem)",
        hovertemplate="<b>%{x}</b><br>Gap: %{y:+.4f}<extra></extra>",
    ))
    fig_gap.add_hline(y=0, line_color=rgba(MUTED, 0.6), line_width=1)
    fig_gap.add_annotation(
        x=ANO_MAX, y=gap.dropna().iloc[-1] if len(gap.dropna()) > 0 else 0,
        text="Positivo = maior IDH masculino",
        showarrow=False, font=dict(color=MUTED, size=10),
        xanchor="right",
    )
    fig_gap.update_layout(**base_layout(
        title="<b>Gap IDH</b> Masculino − Feminino", height=260,
    ))

    # Escolaridade por gênero
    dr_e = dr[(dr["expectativa_de_anos_escola_feminina"] > 0)].copy()
    fig_esc = go.Figure()
    if "expectativa_de_anos_escola_feminina" in dr_e.columns:
        fig_esc.add_trace(go.Bar(
            x=dr_e["ano_referencia"], y=dr_e["expectativa_de_anos_escola_feminina"],
            name="Feminino", marker_color=PURPLE,
            marker_line_color=BORDER, marker_line_width=0.5,
            hovertemplate="<b>%{x}</b><br>Fem.: %{y:.1f} anos<extra></extra>",
        ))
    if "expectativa_de_anos_escola_masculina" in dr_e.columns:
        fig_esc.add_trace(go.Bar(
            x=dr_e["ano_referencia"], y=dr_e["expectativa_de_anos_escola_masculina"],
            name="Masculino", marker_color=TEAL,
            marker_line_color=BORDER, marker_line_width=0.5,
            hovertemplate="<b>%{x}</b><br>Masc.: %{y:.1f} anos<extra></extra>",
        ))
    fig_esc.update_layout(**base_layout(
        title="<b>Anos de Escola</b> por Gênero", barmode="group", height=260,
    ))

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
    Input("cen-slider-start", "value"),
    Input("cen-slider-end",   "value"),
    Input("cen-agr",          "value"),
    Input("cen-sigma",        "value"),
    Input("cen-banda",        "data"),
)
def cb_cenarios(a, b, agr, sigma, banda):
    a = a or ANO_MIN
    b = b or ANO_MAX
    if a > b:
        a, b = b, a
    dr = df_real[(df_real["ano_referencia"] >= a) & (df_real["ano_referencia"] <= b)].copy()
    df = df_fake[(df_fake["ano_referencia"] >= a) & (df_fake["ano_referencia"] <= b)].copy()

    fn    = agr if agr in ("mean", "median", "min", "max") else "mean"
    agr_l = {"mean": "Média", "median": "Mediana", "min": "Mínimo", "max": "Máximo"}[fn]

    # Banda só faz sentido para mean/median (std tem significado estatístico)
    show_banda = ("show" in (banda or [])) and fn in ("mean", "median")

    fake_agg = df.groupby("ano_referencia").agg(
        idh_agr  =("idh", fn),
        idh_std  =("idh", "std"),
        vida_agr =("expectativa_de_vida", fn),
    ).reset_index().dropna(subset=["idh_agr"])

    real_m = dr["idh"].dropna().mean()          if len(dr) > 0 else 0
    fake_m = fake_agg["idh_agr"].mean()         if len(fake_agg) > 0 else 0
    diff   = abs(real_m - fake_m)
    std_v  = df["idh"].dropna().std()           if len(df) > 0 else 0

    # ── Comparação com banda ─────────────────────────────────────────────────
    fig_cmp = go.Figure()
    if show_banda and len(fake_agg) >= 2:
        std_col = fake_agg["idh_std"].fillna(0)
        upper   = (fake_agg["idh_agr"] + sigma * std_col).tolist()
        lower   = (fake_agg["idh_agr"] - sigma * std_col).tolist()
        anos_f  = fake_agg["ano_referencia"].tolist()
        # Garante listas do mesmo tamanho antes de fechar o polígono
        if len(anos_f) == len(upper) == len(lower):
            fig_cmp.add_trace(go.Scatter(
                x=anos_f + anos_f[::-1],
                y=upper + lower[::-1],
                fill="toself", fillcolor=rgba(AMBER, 0.10),
                line=dict(width=0), hoverinfo="skip",
                showlegend=True, name=f"Banda ±{sigma}σ",
            ))

    if len(fake_agg) > 0:
        fig_cmp.add_trace(go.Scatter(
            x=fake_agg["ano_referencia"], y=fake_agg["idh_agr"],
            name=f"Sintético ({agr_l})", mode="lines",
            line=dict(color=AMBER, width=2.5, dash="dash"),
            hovertemplate=f"<b>%{{x}}</b><br>Sint. ({agr_l}): %{{y:.3f}}<extra></extra>",
        ))

    fig_cmp.add_trace(go.Scatter(
        x=dr["ano_referencia"], y=dr["idh"],
        name="IDH Real (PNUD)", mode="lines+markers",
        line=dict(color=TEAL, width=3.5),
        marker=dict(size=6, color=TEAL, line=dict(width=2, color=BG)),
        hovertemplate="<b>%{x}</b><br>IDH Real: %{y:.3f}<extra></extra>",
    ))
    fig_cmp.update_layout(**base_layout(
        title=f"<b>IDH Real vs Sintético</b> ({agr_l}) · {a}–{b}", height=310,
    ))

    # ── Scatter correlação ───────────────────────────────────────────────────
    merged = dr.merge(fake_agg[["ano_referencia","idh_agr"]], on="ano_referencia", how="inner")
    fig_sc = go.Figure()
    if len(merged) >= 2:
        lims = [
            min(merged["idh"].min(), merged["idh_agr"].min()) - 0.01,
            max(merged["idh"].max(), merged["idh_agr"].max()) + 0.01,
        ]
        fig_sc.add_trace(go.Scatter(
            x=lims, y=lims, mode="lines",
            line=dict(color=rgba(ROSE, 0.6), width=1.5, dash="dot"),
            name="Linha 1:1 (perfeito)", hoverinfo="skip",
        ))
        fig_sc.add_trace(go.Scatter(
            x=merged["idh"], y=merged["idh_agr"],
            mode="markers+text", name="Ano",
            text=merged["ano_referencia"].astype(str),
            textposition="top center",
            textfont=dict(size=9, color=MUTED, family=FONT),
            marker=dict(size=9, color=TEAL,
                        line=dict(width=1.5, color=BG), opacity=0.9),
            hovertemplate="<b>%{text}</b><br>Real: %{x:.3f}<br>Sint.: %{y:.3f}<extra></extra>",
        ))
    fig_sc.update_layout(**base_layout(
        title=f"<b>Correlação</b> Real × Sintético ({agr_l})",
        height=280,
        xaxis=dict(title="IDH Real",
                   gridcolor=rgba(BORDER, 0.8), tickfont=dict(color=MUTED, size=11)),
        yaxis=dict(title=f"IDH Sint. ({agr_l})",
                   gridcolor=rgba(BORDER, 0.8), tickfont=dict(color=MUTED, size=11)),
    ))

    # ── Expectativa de vida ──────────────────────────────────────────────────
    fig_vida = go.Figure()
    fig_vida.add_trace(go.Scatter(
        x=dr["ano_referencia"], y=dr["expectativa_de_vida"],
        name="Real (PNUD)", mode="lines+markers",
        line=dict(color=TEAL, width=3),
        marker=dict(size=5, color=TEAL, line=dict(width=1.5, color=BG)),
        hovertemplate="<b>%{x}</b><br>Real: %{y:.1f} anos<extra></extra>",
    ))
    if len(fake_agg) > 0 and "vida_agr" in fake_agg.columns:
        fig_vida.add_trace(go.Scatter(
            x=fake_agg["ano_referencia"], y=fake_agg["vida_agr"],
            name=f"Sint. ({agr_l})", mode="lines",
            line=dict(color=AMBER, width=2.5, dash="dash"),
            hovertemplate=f"<b>%{{x}}</b><br>Sint. ({agr_l}): %{{y:.1f}} anos<extra></extra>",
        ))
    fig_vida.update_layout(**base_layout(
        title="<b>Expectativa de Vida</b>: Real vs Sintético", height=280,
    ))

    # ── Boxplot ──────────────────────────────────────────────────────────────
    anos_box = sorted(df["ano_referencia"].dropna().unique())
    step     = max(1, len(anos_box) // 12)
    fig_box  = go.Figure()
    for ano in anos_box[::step]:
        sub = df[df["ano_referencia"] == ano]["idh"].dropna()
        if len(sub) > 1:
            fig_box.add_trace(go.Box(
                y=sub, name=str(int(ano)),
                marker_color=PURPLE,
                line_color=PURPLE,
                fillcolor=rgba(PURPLE, 0.12),
                showlegend=False, boxmean="sd",
                hovertemplate=f"<b>{int(ano)}</b><br>IDH: %{{y:.3f}}<extra></extra>",
            ))
    fig_box.update_layout(**base_layout(
        title="<b>Distribuição IDH Sintético por Ano</b> — com desvio padrão",
        height=300,
        xaxis=dict(title="Ano", gridcolor=rgba(BORDER, 0.8),
                   tickfont=dict(color=MUTED, size=11)),
        yaxis=dict(title="IDH",  gridcolor=rgba(BORDER, 0.8),
                   tickfont=dict(color=MUTED, size=11)),
    ))

    return (
        f"{real_m:.3f}",
        f"{fake_m:.3f}",
        f"{diff:.4f}",
        f"{std_v:.4f}",
        f"{len(df):,}".replace(",", "."),
        fig_cmp, fig_sc, fig_vida, fig_box,
    )


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(debug=False, port=port)
