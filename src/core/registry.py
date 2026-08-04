import os
import glob
import importlib.util
from typing import Dict, List, Type
from src.core.interfaces import Plugin, Importer, Analyzer, Compiler, Exporter

class PluginRegistry:
    _plugins: Dict[str, Dict] = {}
    
    _importers: List[Importer] = []
    _analyzers: List[Analyzer] = []
    _compilers: List[Compiler] = []
    _exporters: List[Exporter] = []
    
    _enabled: Dict[str, bool] = {}

    @classmethod
    def register(cls, plugin_instance: Plugin):
        name = plugin_instance.name
        
        cls._plugins[name] = {
            "name": name,
            "version": plugin_instance.version,
            "author": plugin_instance.author,
            "description": plugin_instance.description,
            "plugin_type": plugin_instance.plugin_type,
            "supported_inputs": plugin_instance.supported_inputs,
            "supported_outputs": plugin_instance.supported_outputs,
            "instance": plugin_instance
        }
        
        cls._enabled[name] = True

        p_type = plugin_instance.plugin_type.lower()
        if p_type == "importer":
            cls._importers.append(plugin_instance)
        elif p_type == "analyzer":
            cls._analyzers.append(plugin_instance)
        elif p_type == "compiler":
            cls._compilers.append(plugin_instance)
        elif p_type == "exporter":
            cls._exporters.append(plugin_instance)

    @classmethod
    def enable_plugin(cls, name: str):
        if name in cls._plugins:
            cls._enabled[name] = True

    @classmethod
    def disable_plugin(cls, name: str):
        if name in cls._plugins:
            cls._enabled[name] = False

    @classmethod
    def is_enabled(cls, name: str) -> bool:
        return cls._enabled.get(name, False)

    @classmethod
    def get_importers(cls) -> List[Importer]:
        return [p for p in cls._importers if cls.is_enabled(p.name)]

    @classmethod
    def get_analyzers(cls) -> List[Analyzer]:
        return [p for p in cls._analyzers if cls.is_enabled(p.name)]

    @classmethod
    def get_compilers(cls) -> List[Compiler]:
        return [p for p in cls._compilers if cls.is_enabled(p.name)]

    @classmethod
    def get_exporters(cls) -> List[Exporter]:
        return [p for p in cls._exporters if cls.is_enabled(p.name)]

    @classmethod
    def discover_plugins(cls, base_dir: str):
        """Dynamically load all Python modules in plugin directories."""
        plugin_dirs = ['src/importers', 'src/analyzers', 'src/compiler', 'src/exporters']
        
        for p_dir in plugin_dirs:
            full_dir = os.path.join(base_dir, p_dir)
            if not os.path.exists(full_dir):
                continue
                
            for file_path in glob.glob(os.path.join(full_dir, "*.py")):
                if os.path.basename(file_path) == "__init__.py":
                    continue
                
                module_name = p_dir.replace("/", ".") + "." + os.path.basename(file_path)[:-3]
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    try:
                        spec.loader.exec_module(module)
                        
                        # Find classes that inherit from Plugin
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if isinstance(attr, type) and issubclass(attr, Plugin) and attr is not Plugin and not attr_name.startswith('_'):
                                if attr.__name__ in ['Importer', 'Analyzer', 'Compiler', 'Exporter']:
                                    continue
                                
                                # Instantiate and register
                                instance = attr()
                                cls.register(instance)
                    except Exception as e:
                        print(f"Error loading plugin {file_path}: {e}")
