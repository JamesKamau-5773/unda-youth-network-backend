"""Minimal OpenTelemetry instrumentation setup.

Import and call `init_tracing(app)` early in `create_app()` if you want tracing.
This file is a safe stub — importing will not fail if OpenTelemetry packages are missing.
"""
def init_tracing(app):
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.instrumentation.flask import FlaskInstrumentor

        provider = TracerProvider()
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        trace.set_tracer_provider(provider)
        FlaskInstrumentor().instrument_app(app)
    except Exception:
        # If opentelemetry not installed or misconfigured, keep running without tracing
        pass
