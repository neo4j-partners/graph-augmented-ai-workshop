"""
DSPy Language Model Configuration for Databricks Supervisor Agent.

This module handles the configuration of DSPy to work with Databricks
Supervisor Agent endpoints created in Lab 6. It supports both
automatic authentication when running on Databricks and manual authentication
via environment variables.

The Supervisor Agent endpoint routes queries to the Genie + Knowledge Assistant for combined
structured and unstructured data analysis.

References:
    - https://docs.databricks.com/aws/en/generative-ai/dspy/
    - https://dspy.ai/learn/programming/language_models/
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Final

import dspy
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT: Final[Path] = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

# Clear conflicting auth methods - use only HOST + TOKEN from .env
_CONFLICTING_AUTH_VARS: Final[tuple[str, ...]] = (
    "DATABRICKS_CONFIG_PROFILE",
    "DATABRICKS_CLIENT_ID",
    "DATABRICKS_CLIENT_SECRET",
    "DATABRICKS_ACCOUNT_ID",
)
for var in _CONFLICTING_AUTH_VARS:
    os.environ.pop(var, None)


# Default Supervisor Agent endpoint name (from Lab 6)
# Override via SUPERVISOR_AGENT_ENDPOINT environment variable if needed
# Note: Databricks uses the "mas-" prefix in endpoint names (Multi-Agent Supervisor)
DEFAULT_ENDPOINT: Final[str] = os.environ.get("SUPERVISOR_AGENT_ENDPOINT", "mas-3ae5a347-endpoint")


class DatabricksResponsesLM(dspy.BaseLM):
    """
    DSPy LM adapter for Databricks Supervisor Agent endpoints.

    Subclasses ``dspy.BaseLM`` and overrides ``forward()`` (not ``__call__``)
    so that DSPy's built-in caching, callbacks, and history tracking all work
    correctly.  Uses ``model_type="responses"`` so the base class routes
    output extraction through ``_process_response()``.

    The Supervisor Agent endpoint uses the Responses API format::

        POST /responses  {"input": [{"role": "user", "content": "..."}]}

    Supervisor Agent endpoints only support single-turn conversations, so multi-turn
    messages produced by DSPy's ChatAdapter are combined into one user
    message before sending.

    Authentication is handled automatically by WorkspaceClient:
    - On Databricks: Uses runtime's built-in authentication
    - Locally: Uses DATABRICKS_HOST and DATABRICKS_TOKEN from environment
    """

    def __init__(
        self,
        model: str,
        **kwargs: Any,
    ) -> None:
        """
        Initialize the Databricks Responses API LM.

        Args:
            model: The Databricks Supervisor Agent endpoint name from Lab 6.
            **kwargs: Additional arguments (temperature, max_tokens, etc.)
        """
        self._client: Any = None

        # model_type="responses" tells BaseLM._process_lm_response to use
        # _process_response() which understands the Responses API output format.
        super().__init__(model=model, model_type="responses", **kwargs)

    def _get_client(self) -> Any:
        """Lazily create the Databricks OpenAI-compatible client."""
        if self._client is not None:
            return self._client

        try:
            from databricks_openai import DatabricksOpenAI

            self._client = DatabricksOpenAI()
            return self._client
        except Exception as e:
            raise RuntimeError(f"Failed to create Databricks client: {e}")

    def forward(
        self,
        prompt: str | None = None,
        messages: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> Any:
        """
        Call the Supervisor Agent endpoint and return the raw OpenAI response object.

        BaseLM.__call__ (with @with_callbacks) invokes this method, then
        passes the return value through _process_lm_response() for history
        tracking, caching, and output extraction.

        Args:
            prompt: Optional prompt string (converted to user message).
            messages: List of message dicts with role and content.
            **kwargs: Additional arguments forwarded by BaseLM.

        Returns:
            An OpenAI Responses API object that BaseLM._process_response()
            can parse (response.output[].content[].text).
        """
        client = self._get_client()

        # Combine multi-turn messages into a single user message for Supervisor Agent
        if messages:
            parts = []
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "system":
                    parts.append(content)
                elif role == "user":
                    parts.append(content)
                elif role == "assistant":
                    parts.append(f"Assistant: {content}")
            input_messages = [{"role": "user", "content": "\n\n".join(parts)}]
        elif prompt:
            input_messages = [{"role": "user", "content": prompt}]
        else:
            raise ValueError("Either prompt or messages must be provided")

        response = client.responses.create(
            model=self.model,
            input=input_messages,
        )

        # Ensure usage is present — Supervisor Agent endpoints may not return token counts,
        # but BaseLM._process_lm_response() calls dict(response.usage).
        if not hasattr(response, "usage") or response.usage is None:
            response.usage = SimpleNamespace(
                prompt_tokens=0, completion_tokens=0, total_tokens=0,
            )

        return response


def get_lm(
    model_name: str | None = None,
    temperature: float = 0.1,
    max_tokens: int = 4000,
) -> DatabricksResponsesLM:
    """
    Create a DSPy Language Model configured for Databricks Supervisor Agent endpoint.

    This function ONLY supports Supervisor Agent endpoints from Lab 6.
    The Supervisor Agent endpoint uses the Databricks Responses API format, which requires
    a custom LM adapter (DatabricksResponsesLM).

    Authentication is handled automatically by WorkspaceClient:
    - On Databricks: Uses runtime's built-in authentication
    - Locally: Uses DATABRICKS_HOST and DATABRICKS_TOKEN from .env

    Args:
        model_name: The Supervisor Agent endpoint name from Lab 6. If None, uses DEFAULT_ENDPOINT.
        temperature: Sampling temperature (0.0-1.0). Lower = more deterministic.
        max_tokens: Maximum tokens in the response.

    Returns:
        Configured DatabricksResponsesLM instance for the Supervisor Agent endpoint.

    Raises:
        RuntimeError: If Databricks authentication fails.
    """
    endpoint = model_name or DEFAULT_ENDPOINT

    # DatabricksResponsesLM is specifically designed for Supervisor Agent endpoints
    # which use the Responses API format (not OpenAI Chat Completions)
    lm = DatabricksResponsesLM(
        model=endpoint,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return lm


def configure_dspy(
    model_name: str | None = None,
    temperature: float = 0.1,
    max_tokens: int = 4000,
    track_usage: bool = True,
) -> DatabricksResponsesLM:
    """
    Configure DSPy globally with the Databricks Supervisor Agent endpoint.

    This sets up the default LM for all DSPy operations.
    Call this once at application startup.

    This function ONLY supports Supervisor Agent endpoints from Lab 6.
    Uses DatabricksResponsesLM (Responses API format, not OpenAI format).
    ChatAdapter is the default in DSPy 3.x and does not need to be set
    explicitly.

    Args:
        model_name: The Supervisor Agent endpoint name from Lab 6. If None, uses DEFAULT_ENDPOINT.
        temperature: Sampling temperature (0.0-1.0).
        max_tokens: Maximum tokens in the response.
        track_usage: If True, enable token usage tracking.

    Returns:
        The configured LM instance.

    Example:
        >>> from lab_7_augmentation_agent.dspy_modules import configure_dspy
        >>> lm = configure_dspy()
        >>> print(f"Configured with endpoint: {lm.model}")
    """
    lm = get_lm(
        model_name=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # ChatAdapter is the default in DSPy 3.x — no need to set explicitly.
    dspy.configure(
        lm=lm,
        track_usage=track_usage,
    )

    print(f"[OK] DSPy configured")
    print(f"    Endpoint: {model_name or DEFAULT_ENDPOINT}")
    print(f"    Adapter: ChatAdapter (default)")
    print(f"    Temperature: {temperature}")
    print(f"    Max tokens: {max_tokens}")

    return lm


def setup_mlflow_tracing() -> bool:
    """
    Enable MLflow tracing for DSPy operations.

    MLflow provides automatic tracing for DSPy modules, capturing
    inputs, outputs, and intermediate reasoning steps.

    Returns:
        True if tracing was enabled, False otherwise.

    References:
        - https://docs.databricks.com/aws/en/mlflow3/genai/tracing/integrations/dspy
    """
    try:
        import mlflow

        mlflow.dspy.autolog()
        print("[OK] MLflow DSPy tracing enabled")
        return True
    except ImportError:
        print("[WARN] MLflow not installed, tracing disabled")
        print("       Install with: pip install 'mlflow[databricks]>=3.1'")
        return False
    except AttributeError:
        # Older MLflow versions may not have dspy.autolog
        try:
            mlflow.openai.autolog()
            print("[OK] MLflow OpenAI tracing enabled (DSPy tracing requires MLflow 3.1+)")
            return True
        except Exception:
            print("[WARN] MLflow tracing setup failed")
            return False
    except Exception as e:
        print(f"[WARN] MLflow tracing setup failed: {e}")
        return False
