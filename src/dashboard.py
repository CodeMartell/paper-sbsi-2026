"""Read persisted outputs; all rules/calculations belong to the pipeline."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
import streamlit as st
from src.config import settings
from src.review import history, record_review
from src.provenance import digest


def main():
    st.set_page_config(page_title="Conferência gerencial", layout="wide")
    st.title("Conferência gerencial")
    st.caption("Resultados automáticos preservados • revisão humana local e autodeclarada")
    runs = Path(settings.output_dir) / "runs"
    folders = sorted([p.parent for p in runs.glob("*/result.json")], reverse=True)
    if not folders:
        st.info("Nenhuma execução disponível. Execute python -m src.main --local.")
        return
    folder = st.selectbox("Execução", folders, format_func=lambda p: p.name)
    result = json.loads((folder / "result.json").read_text(encoding="utf-8"))
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if any(digest(folder / name) != expected for name, expected in manifest["artifacts"].items()):
        st.error("Artefato alterado após a execução. Conferência bloqueada; preserve os arquivos e investigue a alteração.")
        return
    status = result["state"].upper()
    if not result["publication_allowed"]:
        st.error(f"{status} — publicação bloqueada; sem conclusão operacional liberada.")
    elif result["provisional"]:
        st.warning(f"{status} — relatório provisório. Confira as limitações antes de decidir.")
    else:
        st.success(status)
    for limitation in result["limitations"]:
        st.write(limitation)
    st.subheader("Fontes e atualidade na data da execução")
    st.caption("Obtenção e referência são diferentes. Ao reprocessar, a atualidade é reavaliada.")
    modes = {"current_extraction": "Extração pelo GERP", "contingency": "Contingência", "local_file": "Arquivo local", "synthetic_file": "Arquivo sintético"}
    freshness_labels = {"current": "Atual", "stale": "Desatualizada", "unknown": "Desconhecida"}
    source_rows = []
    for name, source in result["sources"].items():
        meta = source["metadata"]
        source_rows.append({"Fonte": {"finance": "Financeiro", "production": "Produção"}.get(name, name),
            "Modo": modes.get(source["mode"], source["mode"]),
            "Atualidade": freshness_labels[source["freshness"]["state"]],
            "Início da referência": meta.get("reference_start", "Desconhecido"),
            "Fim da referência": meta.get("reference_end", "Desconhecido"),
            "Obtido em": meta.get("obtained_at", "Desconhecido")})
    st.dataframe(pd.DataFrame(source_rows), use_container_width=True, hide_index=True)
    st.write("Registros recebidos, válidos, rejeitados e analisados por fonte")
    st.dataframe(pd.DataFrame(result["counts"]).T, use_container_width=True)
    operational, quality = result["operational"], result["quality"]
    left, right = st.columns(2)
    left.metric("Divergências operacionais", sum(p["classificacao"] != "NORMAL" for p in operational))
    right.metric("Ocorrências de qualidade", len(quality))
    st.subheader("Análise operacional")
    classes = st.multiselect("Classificação", sorted({p["classificacao"] for p in operational}))
    filtered = [p for p in operational if not classes or p["classificacao"] in classes]
    st.dataframe(pd.DataFrame(filtered), use_container_width=True)
    if filtered:
        item = st.selectbox("Detalhar registro e valores utilizados", filtered, format_func=lambda p: p["codigo_projeto"])
        st.write(item["motivo"])
        with st.expander("Valores e indicadores do registro"):
            st.json(item)
    st.subheader("Qualidade dos dados — independente da classificação operacional")
    kinds = st.multiselect("Tipo de problema", sorted({p["type"] for p in quality}))
    filtered_quality = [p for p in quality if not kinds or p["type"] in kinds]
    st.dataframe(pd.DataFrame(filtered_quality), use_container_width=True)
    if filtered_quality:
        item = st.selectbox("Detalhar problema", filtered_quality, format_func=lambda p: f"{p['id']}: {p['type']} / {p['key']}")
        st.write(f"Tratamento: {item['decision']}; linhas de entrada: {item['rows']}")
        with st.expander("Valores originais e decisão de tratamento"):
            st.json([d for d in result["decisions"] if d["source"] == item["source"] and d["row"] in item["rows"]])
    with st.expander("Decisões por linha de entrada"):
        st.dataframe(pd.DataFrame(result["decisions"]), use_container_width=True)
    st.subheader("Revisão humana")
    st.caption("Sem autenticação: responsável autodeclarado. Histórico local editável por quem tem acesso aos arquivos; não é assinatura digital. A revisão não desbloqueia a execução nem altera a classificação automática.")
    reviews = history(folder)
    latest = {r["occurrence_id"]: r["state"] for r in reviews}
    occurrences = quality + [p for p in operational if p["classificacao"] != "NORMAL"]
    if occurrences:
        occurrence = st.selectbox("Ocorrência", occurrences, format_func=lambda p: f"{p['id']} — {latest.get(p['id'], 'pendente')} — {p.get('type', p.get('codigo_projeto'))}")
        with st.form("review"):
            state = st.selectbox("Decisão humana", ["pendente", "confirmada", "descartada"])
            reviewer = st.text_input("Responsável autodeclarado")
            justification = st.text_area("Justificativa")
            if st.form_submit_button("Registrar revisão"):
                try:
                    record_review(folder, occurrence["id"], state, justification, reviewer)
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
    st.dataframe(pd.DataFrame(reviews), use_container_width=True)
    st.subheader("Exportar evidências da execução")
    st.caption("O JSON inclui estado e limitações. Relatórios bloqueados são diagnósticos, não resultados gerenciais válidos.")
    for name in ("result.json", "manifest.json", "relatorio.txt", "policy.json"):
        if (folder / name).exists():
            st.download_button(name, (folder / name).read_bytes(), file_name=f"{folder.name}_{name}")
    st.download_button("Histórico de revisões", json.dumps(reviews, ensure_ascii=False, indent=2), file_name=f"{folder.name}_reviews.json")
    with st.expander("Metadados e tempos das etapas"):
        st.json(manifest)


if __name__ == "__main__":
    main()
