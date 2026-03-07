"""DejiTech Mockup - Professional device mockup video generator."""

__version__ = "2.1.0"

def main():
    """Entry point that imports main module on demand."""
    from dejitech_mockup.main import main as _main
    _main()

def get_app():
    """Get the Typer app instance."""
    from dejitech_mockup.main import app
    return app

__all__ = ["main", "get_app", "__version__"]
