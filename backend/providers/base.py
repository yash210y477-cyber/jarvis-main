from abc import ABC, abstractmethod


class BaseProvider(ABC):

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def health(self) -> bool:
        pass

    @abstractmethod
    def chat(self, prompt: str) -> dict:
        pass

    def success(self, response):

        return {
            "success": True,
            "provider": self.name(),
            "response": response
        }

    def failure(self, error):

        return {
            "success": False,
            "provider": self.name(),
            "error": str(error)
        }