"""Model-agnostic agent integration contracts for OKP."""
from .models import AgentContextRequest, AgentContextPackage, ContextItem
from .context_gateway import ContextGateway, ContextAccessError
__all__ = ["AgentContextRequest", "AgentContextPackage", "ContextItem", "ContextGateway", "ContextAccessError"]
