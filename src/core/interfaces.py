from abc import ABC, abstractmethod
from typing import List, Any
from src.models.knowledge_package import KnowledgePackage

class Plugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        pass

    @property
    @abstractmethod
    def author(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    @abstractmethod
    def plugin_type(self) -> str:
        pass

    @property
    @abstractmethod
    def supported_inputs(self) -> List[str]:
        pass

    @property
    @abstractmethod
    def supported_outputs(self) -> List[str]:
        pass

class Importer(Plugin):
    @abstractmethod
    def import_data(self, package: KnowledgePackage) -> KnowledgePackage:
        pass

class Analyzer(Plugin):
    @abstractmethod
    def analyze(self, package: KnowledgePackage) -> KnowledgePackage:
        pass

class Compiler(Plugin):
    @abstractmethod
    def compile(self, package: KnowledgePackage) -> KnowledgePackage:
        pass

class Exporter(Plugin):
    @abstractmethod
    def export(self, package: KnowledgePackage) -> KnowledgePackage:
        pass
