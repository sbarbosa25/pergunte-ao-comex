"""Pergunte ao Comex: perguntas em português respondidas com SQL gerado por IA."""

from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CSV_BRUTO = RAIZ / "dados" / "processos_comex.csv"
BANCO = RAIZ / "dados" / "comex.duckdb"

__version__ = "0.1.0"
