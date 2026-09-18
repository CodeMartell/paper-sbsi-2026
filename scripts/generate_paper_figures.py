"""Generate publication-ready figures for the SBSI research paper."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.sans-serif": "Arial",
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "figure.titlesize": 14,
    "figure.titleweight": "bold",
})


def generate_fig1_architecture():
    """Figure 1: Architectural diagram of the DSR Artifact."""
    fig, ax = plt.subplots(figsize=(13, 7), dpi=300)
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 7.5)
    ax.axis("off")

    ax.text(6.5, 7.1, "Arquitetura do Artefato DSR para Integração Rastreável de Dados", 
            ha="center", va="center", fontsize=13, fontweight="bold", color="#111827")

    stages = [
        (0.5, 1.2, 2.1, 4.8, "1. Ingestão & Fontes", 
         "• GERP Fake (Playwright)\n• Fallback Contingencial\n• Produção Física (XLSX)\n• Circuit Breaker\n• Preservação Binária", 
         "#F0FDF4", "#16A34A"),
        (2.9, 1.2, 2.2, 4.8, "2. Portas de Qualidade", 
         "• Validação de Esquema\n• Chaves Obrigatórias\n• Números Finitos\n• Duplicatas Conflitantes\n• Denominador Não-Zero\n• Ledger de Ocorrências", 
         "#FEF2F2", "#DC2626"),
        (5.4, 1.2, 2.2, 4.8, "3. Proveniência Forte", 
         "• Hashes SHA-256 (Insumos)\n• Hash de Versão de Código\n• Metadados Temporais\n  (reference vs obtained)\n• Manifesto JSON\n• Replay Determinístico", 
         "#EFF6FF", "#2563EB"),
        (7.9, 1.2, 2.2, 4.8, "4. Motor de Integração", 
         "• Outer-Join Rastreável\n• Detecção Sem-Par\n• Desvio Financeiro (%)\n• Desvio Produção (%)\n• Regras de Negócio\n  (Normal/Atenção/Crítico)", 
         "#FAF5FF", "#9333EA"),
        (10.4, 1.2, 2.1, 4.8, "5. Decisão & Supervisão", 
         "• Relatório Textual (TXT)\n• Estruturado (JSON)\n• Dashboard Streamlit\n• Human-in-the-Loop\n• Histórico de Revisões\n  em SQLite Isolado", 
         "#FFFBEB", "#D97706"),
    ]

    for x, y, w, h, title, content, bg_col, border_col in stages:
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1,rounding_size=0.15",
                                      facecolor=bg_col, edgecolor=border_col, linewidth=1.8)
        ax.add_patch(rect)
        
        header_rect = patches.FancyBboxPatch((x, y + h - 0.7), w, 0.7, boxstyle="round,pad=0.08,rounding_size=0.1",
                                            facecolor=border_col, edgecolor=border_col, linewidth=1)
        ax.add_patch(header_rect)
        ax.text(x + w / 2, y + h - 0.35, title, ha="center", va="center", color="white", fontsize=9.5, fontweight="bold")
        ax.text(x + 0.12, y + h - 0.95, content, ha="left", va="top", color="#1F2937", fontsize=8.5, linespacing=1.6)

    arrow_props = dict(arrowstyle="-|>", color="#4B5563", lw=2, mutation_scale=16)
    for i in range(len(stages) - 1):
        x_start = stages[i][0] + stages[i][2] + 0.05
        x_end = stages[i+1][0] - 0.05
        y_mid = 3.6
        ax.annotate("", xy=(x_end, y_mid), xytext=(x_start, y_mid), arrowprops=arrow_props)

    note_rect = patches.FancyBboxPatch((0.5, 0.25), 12.0, 0.65, boxstyle="round,pad=0.05,rounding_size=0.08",
                                      facecolor="#F3F4F6", edgecolor="#9CA3AF", linewidth=1)
    ax.add_patch(note_rect)
    ax.text(6.5, 0.58, "Princípios Centrais de SI Organizacional Incorporados no Artefato", 
            ha="center", va="center", fontsize=8.5, fontweight="bold", color="#374151")
    ax.text(6.5, 0.40, "Separação entre Qualidade de Dados e Negócio • Rastreabilidade Imutável • Transparência de Limitações ao Decisor Humano", 
            ha="center", va="center", fontsize=8, color="#4B5563")

    plt.tight_layout()
    output_path = OUTPUT_DIR / "fig1_arquitetura_artefato_dsr.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


def generate_fig2_quality_gate():
    """Figure 2: Quality gate decision flow."""
    fig, ax = plt.subplots(figsize=(11, 7), dpi=300)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 7.5)
    ax.axis("off")

    ax.text(5.5, 7.1, "Fluxo de Decisão e Governança da Porta de Qualidade", 
            ha="center", va="center", fontsize=13, fontweight="bold", color="#111827")

    ax.add_patch(patches.FancyBboxPatch((4.0, 6.0), 3.0, 0.65, boxstyle="round,pad=0.05", facecolor="#3B82F6", edgecolor="#1D4ED8", lw=1.5))
    ax.text(5.5, 6.32, "Insumos Extraídos (CSV / XLSX)", ha="center", va="center", color="white", fontweight="bold", fontsize=9)

    ax.add_patch(patches.FancyBboxPatch((4.0, 4.8), 3.0, 0.7, boxstyle="round,pad=0.05", facecolor="#FEF3C7", edgecolor="#D97706", lw=1.5))
    ax.text(5.5, 5.15, "1. Validação de Esquema\n(colunas obrigatórias presentes?)", ha="center", va="center", color="#92400E", fontsize=8.5, fontweight="bold")

    ax.add_patch(patches.FancyBboxPatch((8.3, 4.8), 2.3, 0.7, boxstyle="round,pad=0.05", facecolor="#FEE2E2", edgecolor="#DC2626", lw=1.5))
    ax.text(9.45, 5.15, "BLOQUEIO TOTAL\n(Execução abortada)", ha="center", va="center", color="#991B1B", fontsize=8, fontweight="bold")

    ax.add_patch(patches.FancyBboxPatch((4.0, 3.5), 3.0, 0.75, boxstyle="round,pad=0.05", facecolor="#FEF3C7", edgecolor="#D97706", lw=1.5))
    ax.text(5.5, 3.87, "2. Integridade dos Registros\n(chave válida, número finito,\nsem duplicata conflitante?)", ha="center", va="center", color="#92400E", fontsize=8, fontweight="bold")

    ax.add_patch(patches.FancyBboxPatch((8.3, 3.5), 2.3, 0.75, boxstyle="round,pad=0.05", facecolor="#FEE2E2", edgecolor="#DC2626", lw=1.5))
    ax.text(9.45, 3.87, "ISOLAMENTO DE LINHA\n(Ledger de Qualidade;\nsem imputação silenciosa)", ha="center", va="center", color="#991B1B", fontsize=8, fontweight="bold")

    ax.add_patch(patches.FancyBboxPatch((4.0, 2.2), 3.0, 0.7, boxstyle="round,pad=0.05", facecolor="#FEF3C7", edgecolor="#D97706", lw=1.5))
    ax.text(5.5, 2.55, "3. Verificação de Atualidade\n(período de referência recente?)", ha="center", va="center", color="#92400E", fontsize=8.5, fontweight="bold")

    ax.add_patch(patches.FancyBboxPatch((0.5, 2.2), 2.5, 0.7, boxstyle="round,pad=0.05", facecolor="#FEF9C3", edgecolor="#CA8A04", lw=1.5))
    ax.text(1.75, 2.55, "MARCAÇÃO PROVISÓRIA\n(Saída com limitações\ne alertas explícitos)", ha="center", va="center", color="#854D0E", fontsize=8, fontweight="bold")

    ax.add_patch(patches.FancyBboxPatch((4.0, 0.8), 3.0, 0.75, boxstyle="round,pad=0.05", facecolor="#DCFCE7", edgecolor="#16A34A", lw=1.5))
    ax.text(5.5, 1.17, "Aplicação de Regras de Negócio\n(Classificação dos válidos:\nNORMAL / ATENÇÃO / CRÍTICO)", ha="center", va="center", color="#166534", fontsize=8.5, fontweight="bold")

    arr = dict(arrowstyle="-|>", color="#374151", lw=1.8, mutation_scale=14)
    ax.annotate("", xy=(5.5, 5.5), xytext=(5.5, 6.0), arrowprops=arr)
    ax.annotate("", xy=(5.5, 4.25), xytext=(5.5, 4.8), arrowprops=arr)
    ax.text(5.65, 4.45, "Sim", fontsize=8, fontweight="bold", color="#16A34A")
    ax.annotate("", xy=(5.5, 2.9), xytext=(5.5, 3.5), arrowprops=arr)
    ax.text(5.65, 3.15, "Sim", fontsize=8, fontweight="bold", color="#16A34A")
    ax.annotate("", xy=(5.5, 1.55), xytext=(5.5, 2.2), arrowprops=arr)
    ax.text(5.65, 1.85, "Sim", fontsize=8, fontweight="bold", color="#16A34A")

    ax.annotate("", xy=(8.3, 5.15), xytext=(7.0, 5.15), arrowprops=arr)
    ax.text(7.4, 5.3, "Não", fontsize=8, fontweight="bold", color="#DC2626")

    ax.annotate("", xy=(8.3, 3.87), xytext=(7.0, 3.87), arrowprops=arr)
    ax.text(7.4, 4.02, "Não", fontsize=8, fontweight="bold", color="#DC2626")

    ax.annotate("", xy=(3.0, 2.55), xytext=(4.0, 2.55), arrowprops=arr)
    ax.text(3.35, 2.7, "Não / Desc.", fontsize=8, fontweight="bold", color="#D97706")

    plt.tight_layout()
    output_path = OUTPUT_DIR / "fig2_porta_qualidade_decisao.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


def generate_fig3_baseline_comparison():
    """Figure 3: Empirical evaluation comparing Historical Baseline vs Enhanced DSR Artifact."""
    fig, ax = plt.subplots(figsize=(9, 5.2), dpi=300)

    categories = [
        "Itens Conformes com\no Oráculo (de 54)",
        "Alertas de Qualidade\nPerdidos (de 27)",
        "Eventos de Erro\nSilencioso Liberados"
    ]
    
    baseline_values = [39, 27, 45]
    enhanced_values = [54, 0, 0]

    x = np.arange(len(categories))
    width = 0.32

    rects1 = ax.bar(x - width/2, baseline_values, width, label="Baseline Histórica (commit 7e1768d)", 
                    color="#DC2626", edgecolor="#991B1B", linewidth=1.2, alpha=0.85)
    rects2 = ax.bar(x + width/2, enhanced_values, width, label="Artefato Aprimorado DSR", 
                    color="#16A34A", edgecolor="#14532D", linewidth=1.2, alpha=0.9)

    ax.set_ylabel("Quantidade de Ocorrências / Itens", fontsize=10, fontweight="bold")
    ax.set_title("Comparação Experimental: Baseline Histórica vs. Artefato DSR Aprimorado\n(18 execuções sintéticas controladas por condição)", 
                 fontsize=11, fontweight="bold", pad=14)
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=9.5, fontweight="bold")
    ax.legend(loc="upper right", frameon=True, fontsize=9.5)
    ax.set_ylim(0, 62)
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    def autolabel(rects, is_enhanced=False):
        for rect in rects:
            height = rect.get_height()
            offset = 1.2
            if height == 0:
                ax.annotate("0\n(0,0%)",
                            xy=(rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, offset),
                            textcoords="offset points",
                            ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#14532D" if is_enhanced else "#991B1B")
            else:
                pct = ""
                if rects == rects1 and height == 39: pct = "\n(72,2%)"
                elif rects == rects2 and height == 54: pct = "\n(100%)"
                elif rects == rects1 and height == 27: pct = "\n(100% perda)"
                elif rects == rects1 and height == 45: pct = "\n(crítico)"

                ax.annotate(f"{height}{pct}",
                            xy=(rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, offset),
                            textcoords="offset points",
                            ha="center", va="bottom", fontsize=8.5, fontweight="bold", color="#14532D" if is_enhanced else "#991B1B")

    autolabel(rects1, False)
    autolabel(rects2, True)

    plt.tight_layout()
    output_path = OUTPUT_DIR / "fig3_avaliacao_comparativa_baseline.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    generate_fig1_architecture()
    generate_fig2_quality_gate()
    generate_fig3_baseline_comparison()
