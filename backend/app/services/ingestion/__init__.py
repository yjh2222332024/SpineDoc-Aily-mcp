"""
Ingestion module — renamed from 'rag'
Backward compatibility: old imports via 'rag' still work via this shim.
"""
# Don't eagerly import all submodules — some have module-level singletons
# that access settings (e.g., coze_harvester) which may fail on import.