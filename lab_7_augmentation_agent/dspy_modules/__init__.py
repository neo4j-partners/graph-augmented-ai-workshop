"""
DSPy Modules for Graph Augmentation Agent.

This package contains the DSPy-based components for structured output generation:
- config: Language model configuration for Databricks
- signatures: DSPy signatures for each analysis type
- analyzers: DSPy modules that perform the actual analysis
- mas_client: Client for querying the Supervisor Agent
"""

from lab_7_augmentation_agent.dspy_modules.config import (
    configure_dspy,
    get_lm,
    setup_mlflow_tracing,
    DatabricksResponsesLM,
)
from lab_7_augmentation_agent.dspy_modules.mas_client import (
    MASClient,
    GapAnalysisResult,
    fetch_gap_analysis,
)
from lab_7_augmentation_agent.dspy_modules.signatures import (
    InvestmentThemesSignature,
    NewEntitiesSignature,
    MissingAttributesSignature,
    ImpliedRelationshipsSignature,
    ANALYSIS_SIGNATURES,
)
from lab_7_augmentation_agent.dspy_modules.analyzers import (
    InvestmentThemesResult,
    NewEntitiesResult,
    MissingAttributesResult,
    ImpliedRelationshipsResult,
    InvestmentThemesAnalyzer,
    NewEntitiesAnalyzer,
    MissingAttributesAnalyzer,
    ImpliedRelationshipsAnalyzer,
    GraphAugmentationAnalyzer,
)

__all__ = [
    # Config
    "configure_dspy",
    "get_lm",
    "setup_mlflow_tracing",
    "DatabricksResponsesLM",
    # MAS Client
    "MASClient",
    "GapAnalysisResult",
    "fetch_gap_analysis",
    # Signatures
    "InvestmentThemesSignature",
    "NewEntitiesSignature",
    "MissingAttributesSignature",
    "ImpliedRelationshipsSignature",
    "ANALYSIS_SIGNATURES",
    # Result types
    "InvestmentThemesResult",
    "NewEntitiesResult",
    "MissingAttributesResult",
    "ImpliedRelationshipsResult",
    # Analyzers
    "InvestmentThemesAnalyzer",
    "NewEntitiesAnalyzer",
    "MissingAttributesAnalyzer",
    "ImpliedRelationshipsAnalyzer",
    "GraphAugmentationAnalyzer",
]
