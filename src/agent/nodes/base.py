"""
Base Node
노드의 기본 구조를 정의하는 모듈입니다.
"""

from abc import ABC, abstractmethod
from typing import Any

from ..state import AgentState


class BaseNode(ABC):
    """
    모든 노드의 기본 클래스입니다.

    각 노드는 이 클래스를 상속받아 __call__ 메서드를 구현해야 합니다.
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def __call__(self, state: AgentState) -> dict[str, Any]:
        """
        노드 실행 메서드입니다.

        Args:
            state: 현재 에이전트 상태

        Returns:
            업데이트할 상태 값들의 딕셔너리
        """
        pass
