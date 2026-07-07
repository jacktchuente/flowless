from abc import ABC, abstractmethod


class LogoGenerationError(Exception):
    pass


class LogoImageBackend(ABC):
    name: str = "base"

    @abstractmethod
    def generate(self, prompt: str) -> bytes:
        """Genere une image PNG a partir du prompt et retourne ses octets."""
