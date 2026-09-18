"""First process instance. Other processes provide loaders, schemas and analyze()."""
from src.quality import FINANCE, PRODUCTION
from src.data_processor import (extrair_dados_financeiros, extrair_dados_producao,
                                cruzar_dados, analisar_e_identificar_divergencias)


class FinanceProduction:
    name = "finance-production"
    version = "1"
    schemas = {"finance": FINANCE, "production": PRODUCTION}
    loaders = {"finance": extrair_dados_financeiros, "production": extrair_dados_producao}

    def analyze(self, frames, settings):
        return analisar_e_identificar_divergencias(cruzar_dados(frames["finance"], frames["production"]), settings)
