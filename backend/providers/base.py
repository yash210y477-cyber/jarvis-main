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